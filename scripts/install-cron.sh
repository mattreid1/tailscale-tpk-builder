#!/bin/bash
# Run on the NAS, as root. Preserves the existing crontab.
set -euo pipefail
export PATH=/usr/local/bin:/usr/local/sbin:/usr/bin:/usr/sbin:/bin:/sbin
STATE=/Volume1/@app-updates/Tailscale
REPO=${TAILSCALE_REPO:?Set TAILSCALE_REPO to owner/repository}
[[ "$REPO" =~ ^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$ ]]
# A generic installation default, independent of any existing NAS deployment.
SCHEDULE=${TAILSCALE_UPDATE_SCHEDULE:-"0 3 * * *"}
[[ "$SCHEDULE" != *$'\n'* && "$SCHEDULE" != *$'\r'* ]]
[[ $(id -u) == 0 ]]
mkdir -p "$STATE"
chmod 700 "$STATE"
cp "$(dirname "$0")/tnas-update.sh" "$STATE/tnas-update.sh"
chmod 700 "$STATE/tnas-update.sh"
crontab -l > "$STATE/crontab.before" 2>/dev/null || true
awk '!/\/Volume1\/@app-updates\/Tailscale\/tnas-update.sh/' "$STATE/crontab.before" > "$STATE/crontab.new"
printf '%s TAILSCALE_REPO=%s %s/tnas-update.sh --update >> %s/update.log 2>&1\n' "$SCHEDULE" "$REPO" "$STATE" "$STATE" >> "$STATE/crontab.new"
crontab "$STATE/crontab.new"
echo 'Update schedule installed in the NAS system timezone.'
crontab -l
