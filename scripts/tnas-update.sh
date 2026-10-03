#!/bin/bash
# Install only upstream-verified tailscale + tailscaled; never package scripts/UI.
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
REPO=${TAILSCALE_REPO:?Set TAILSCALE_REPO to owner/repository}
APP=${TAILSCALE_APP:-/Volume1/@apps/Tailscale}
STATE=${TAILSCALE_UPDATE_DIR:-/Volume1/@app-updates/Tailscale}
MODE=${1:---update}
case "$MODE" in
    --update|--check|--download-only) ;;
    *) echo 'Usage: tnas-update.sh [--check|--download-only|--update]'; exit 2 ;;
esac
log() { printf '[%s] %s\n' "$(date -Iseconds)" "$*"; }
[[ $(id -u) == 0 ]] || { log 'Run as root'; exit 1; }
[[ $(uname -m) == x86_64 && -d "$APP" && ! -L "$APP" ]] || {
    log 'Requires an existing TOS 5 x86_64 Tailscale app directory'; exit 1;
}
[[ "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]] || exit 1
for tool in jq sha256sum md5sum xz tar flock timeout pgrep cmp nohup; do command -v "$tool" >/dev/null; done
CURL=$(command -v ter_curl || command -v curl)
mkdir -p "$STATE"
chmod 700 "$STATE"
exec 9>"$STATE/update.lock"
flock -n 9 || { log 'Another update is running'; exit 0; }
fetch() { "$CURL" --fail --silent --show-error --location --proto '=https' --proto-redir '=https' --retry 3 --connect-timeout 20 --max-time 600 "$@"; }
WORK=$(mktemp -d "$STATE/staging.XXXXXX")
STOPPED=0
SUCCESS=0
BACKUP=''
BIN="$APP/bin/program"
DAEMON_ARGS=()
launch_daemon() {
    # Retain the running daemon's exact arguments, config symlinks, and identity.
    (exec 9>&-; cd "$BIN"; nohup "$BIN/tailscaled" "${DAEMON_ARGS[@]}" >> "$APP/Tailscale_start.log" 2>&1 < /dev/null &)
}
stop_daemon() {
    local pid
    pid=$(pgrep -x tailscaled || true)
    [[ -n "$pid" && "$pid" != *$'\n'* ]] || return 1
    kill -TERM "$pid"
    for attempt in $(seq 1 30); do
        pgrep -x tailscaled >/dev/null || return 0
        sleep 1
    done
    return 1
}
cleanup() {
    result=$?
    trap - EXIT
    if [[ $SUCCESS == 0 && $STOPPED == 1 ]]; then
        log 'Update failed; restoring previous binaries'
        if pgrep -x tailscaled >/dev/null; then stop_daemon || true; fi
        if pgrep -x tailscaled >/dev/null; then
            log 'Daemon did not stop; backup retained for manual recovery'
        else
            for name in tailscale tailscaled; do
                cp -p "$BACKUP/$name" "$BIN/.$name.rollback"
                mv -f "$BIN/.$name.rollback" "$BIN/$name"
            done
            launch_daemon || true
            log 'Previous binaries restored and daemon restarted'
        fi
    fi
    rm -rf "$WORK"
    exit "$result"
}
trap cleanup EXIT
fetch "https://api.github.com/repos/$REPO/releases/latest" -o "$WORK/release.json"
TAG=$(jq -er '.tag_name' "$WORK/release.json")
[[ "$TAG" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]] || { log 'Invalid release tag'; exit 1; }
VERSION=${TAG#v}
CURRENT=$(timeout 10 "$BIN/tailscale" version | head -1)
[[ "$CURRENT" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || { log 'Invalid installed binary version'; exit 1; }
log "Installed binaries: $CURRENT; latest release: $VERSION"
NEWEST=$(printf '%s\n%s\n' "$CURRENT" "$VERSION" | sort -V | tail -1)
if [[ "$CURRENT" == "$VERSION" || "$NEWEST" != "$VERSION" ]]; then
    log 'Already current; no downgrade performed'
    exit 0
fi
[[ "$MODE" != --check ]] || exit 0
ASSET=tailscale-tos5-x86_64.tpk
fetch "https://github.com/$REPO/releases/download/v$VERSION/$ASSET" -o "$WORK/$ASSET"
fetch "https://github.com/$REPO/releases/download/v$VERSION/SHA256SUMS" -o "$WORK/SHA256SUMS"
EXPECTED=$(awk -v name="$ASSET" '$2 == name {print $1}' "$WORK/SHA256SUMS")
[[ "$EXPECTED" =~ ^[a-f0-9]{64}$ ]] || { log 'Missing/invalid SHA256'; exit 1; }
[[ $(sha256sum "$WORK/$ASSET" | awk '{print $1}') == "$EXPECTED" ]] || { log 'Package SHA256 mismatch'; exit 1; }
dd if="$WORK/$ASSET" of="$WORK/header.json" bs=2048 count=1 status=none
jq -e --arg version "$VERSION.0" '.id == "Tailscale" and .platform == "x86_64" and .version == $version' "$WORK/header.json" >/dev/null
dd if="$WORK/$ASSET" of="$WORK/package.xz" bs=10240 skip=1 status=none
[[ $(md5sum "$WORK/package.xz" | awk '{print $1}') == "$(jq -er .md5 "$WORK/header.json")" ]] || exit 1
xz -dc "$WORK/package.xz" > "$WORK/package.tar"
# Read just these two regular members to files. Never extract the package tree.
for name in tailscale tailscaled; do
    details=$(tar -tvf "$WORK/package.tar" "bin/program/$name")
    [[ "$details" == -* && "$details" != *$'\n'* ]] || { log "Invalid $name archive member"; exit 1; }
    tar -xOf "$WORK/package.tar" "bin/program/$name" > "$WORK/$name"
done
# Independent trust anchor: official Tailscale download, not the GitHub publisher.
UPSTREAM="https://pkgs.tailscale.com/stable/tailscale_${VERSION}_amd64.tgz"
fetch "$UPSTREAM" -o "$WORK/upstream.tgz"
EXPECTED=$(fetch "$UPSTREAM.sha256")
[[ "$EXPECTED" =~ ^[a-f0-9]{64}$ ]] || exit 1
[[ $(sha256sum "$WORK/upstream.tgz" | awk '{print $1}') == "$EXPECTED" ]] || { log 'Official tarball checksum mismatch'; exit 1; }
for name in tailscale tailscaled; do
    member="tailscale_${VERSION}_amd64/$name"
    details=$(tar -tzvf "$WORK/upstream.tgz" "$member")
    [[ "$details" == -* && "$details" != *$'\n'* ]] || exit 1
    tar -xzOf "$WORK/upstream.tgz" "$member" > "$WORK/$name.official"
    # Builder changes exactly these three reserved ELF-padding bytes.
    printf TOS | dd of="$WORK/$name.official" bs=1 seek=8 count=3 conv=notrunc status=none
    cmp -s "$WORK/$name" "$WORK/$name.official" || { log "$name differs from official upstream; refusing update"; exit 1; }
    chmod 755 "$WORK/$name"
    [[ $(timeout 10 "$WORK/$name" --version | head -1) == "$VERSION" ]]
done
log "Both packaged binaries match official Tailscale $VERSION; all other package files ignored"
if [[ "$MODE" == --download-only ]]; then
    mkdir -p "$STATE/downloads"
    cp "$WORK/$ASSET" "$STATE/downloads/Tailscale-$VERSION.tpk"
    log "Saved verified package $VERSION without changing the app"
    exit 0
fi
PID=$(pgrep -x tailscaled)
[[ "$PID" =~ ^[0-9]+$ && $(readlink -f "/proc/$PID/exe") == "$BIN/tailscaled" ]]
mapfile -d '' -t SAVED_COMMAND < "/proc/$PID/cmdline"
DAEMON_ARGS=("${SAVED_COMMAND[@]:1}")
OLD_IP=$(timeout 10 "$BIN/tailscale" ip -4)
BACKUP="$STATE/backups/$(date +%Y%m%d-%H%M%S)-$CURRENT"
mkdir -p "$BACKUP"
for name in tailscale tailscaled; do cp -p "$BIN/$name" "$BACKUP/$name"; done
printf '%s\n' "${DAEMON_ARGS[@]}" > "$BACKUP/daemon-args.txt"
log "Replacing only tailscale and tailscaled; backup: $BACKUP"
STOPPED=1
stop_daemon
for name in tailscale tailscaled; do
    cp "$WORK/$name" "$BIN/.$name.new"
    chmod 755 "$BIN/.$name.new"
    mv -f "$BIN/.$name.new" "$BIN/$name"
done
launch_daemon
for attempt in $(seq 1 24); do
    if timeout 10 "$BIN/tailscale" status --json > "$WORK/status.json" 2>/dev/null &&
        jq -e --arg ip "$OLD_IP" '.BackendState == "Running" and (.TailscaleIPs | index($ip) != null)' "$WORK/status.json" >/dev/null; then
        [[ $(timeout 10 "$BIN/tailscale" version | head -1) == "$VERSION" ]]
        SUCCESS=1
        log "Update successful: binaries $VERSION; Tailscale IP retained"
        printf '%s\n' "$BACKUP" > "$STATE/last-backup"
        exit 0
    fi
    sleep 5
done
log 'New daemon failed health check'
exit 1
