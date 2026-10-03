#!/bin/bash
#
# Update Tailscale binaries from official release
#
# Usage: ./update_tailscale.sh [version]
#        ./update_tailscale.sh 1.92.1
#        ./update_tailscale.sh latest
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SRC_DIR="$SCRIPT_DIR/src"
TEMP_DIR=$(mktemp -d)

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

cleanup() {
    rm -rf "$TEMP_DIR"
}
trap cleanup EXIT

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1" >&2
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1" >&2
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1" >&2
}

get_latest_version() {
    curl -fsSL --retry 3 https://pkgs.tailscale.com/stable/?mode=json | \
        python3 -c 'import json,sys; print(json.load(sys.stdin)["TarballsVersion"])'
}

download_and_extract() {
    local version=$1
    local arch=$2
    local url="https://pkgs.tailscale.com/stable/tailscale_${version}_${arch}.tgz"
    local tarball="$TEMP_DIR/tailscale_${version}_${arch}.tgz"

    log_info "Downloading Tailscale $version for $arch..."
    if ! curl -fsSL --retry 3 "$url" -o "$tarball"; then
        log_error "Failed to download $url"
        return 1
    fi

    local expected actual
    expected=$(curl -fsSL --retry 3 "${url}.sha256")
    actual=$(shasum -a 256 "$tarball" | awk '{print $1}')
    [[ "$expected" =~ ^[a-f0-9]{64}$ && "$actual" == "$expected" ]] || {
        log_error "Official tarball SHA256 mismatch"
        return 1
    }
    log_info "Extracting..."
    tar -xzf "$tarball" -C "$TEMP_DIR"

    echo "$TEMP_DIR/tailscale_${version}_${arch}"
}

add_tos_watermark() {
    local binary=$1
    # Add "TOS" watermark to ELF header padding (bytes 8-10)
    # This is in the EI_PAD field which is reserved/unused
    printf 'TOS' | dd of="$binary" bs=1 seek=8 count=3 conv=notrunc 2>/dev/null
}

verify_binary() {
    local binary=$1
    local name=$(basename "$binary")

    if ! file "$binary" | grep -q "ELF 64-bit"; then
        log_error "$name is not a valid ELF binary"
        return 1
    fi

    # Check for Tailscale version string
    if ! strings "$binary" | grep -qE "^v[0-9]+\.[0-9]+\.[0-9]+"; then
        log_warn "$name: Could not find version string"
    fi

    log_info "$name: OK"
    return 0
}

update_version_file() {
    local version=$1
    # Convert 1.92.1 to 1.92.1.0 format
    local full_version="${version}.0"
    echo "$full_version" > "$SRC_DIR/version"
    log_info "Updated version file to $full_version"
}

update_service_script() {
    local version=$1
    local full_version="${version}.0"
    local service_file="$SRC_DIR/init.d/service"

    if [[ -f "$service_file" ]]; then
        sed -i.bak "s/^VERSION=.*/VERSION=\"$full_version\"/" "$service_file"
        rm -f "${service_file}.bak"
        log_info "Updated service script version"
    fi
}

# Main
VERSION=${1:-latest}

if [[ "$VERSION" == "latest" ]]; then
    log_info "Fetching latest version..."
    VERSION=$(get_latest_version)
    if [[ -z "$VERSION" ]]; then
        log_error "Failed to determine latest version"
        exit 1
    fi
fi

[[ "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]] || {
    log_error "Version must be X.Y.Z"
    exit 1
}
log_info "Tailscale version: $VERSION"
log_info "Source directory: $SRC_DIR"

# Download both architectures
EXTRACT_DIR=$(download_and_extract "$VERSION" "amd64")

if [[ ! -d "$EXTRACT_DIR" ]]; then
    log_error "Extraction failed"
    exit 1
fi

# Verify official binaries
log_info "Verifying official binaries..."
verify_binary "$EXTRACT_DIR/tailscale"
verify_binary "$EXTRACT_DIR/tailscaled"

# Show checksums of official binaries
log_info "Official binary checksums:"
shasum -a 256 "$EXTRACT_DIR/tailscale" "$EXTRACT_DIR/tailscaled"

# Copy binaries to source directory
log_info "Installing binaries..."

# Main program directory
cp "$EXTRACT_DIR/tailscale" "$SRC_DIR/bin/program/tailscale"
cp "$EXTRACT_DIR/tailscaled" "$SRC_DIR/bin/program/tailscaled"
chmod 755 "$SRC_DIR/bin/program/tailscale" "$SRC_DIR/bin/program/tailscaled"

# Add TOS watermark
log_info "Adding TOS watermark..."
add_tos_watermark "$SRC_DIR/bin/program/tailscale"
add_tos_watermark "$SRC_DIR/bin/program/tailscaled"

# Sysroot copies are ignored by the builder, which emits symlinks.
mkdir -p "$SRC_DIR/sysroot/usr/local/bin"
cp "$SRC_DIR/bin/program/tailscale" "$SRC_DIR/sysroot/usr/local/bin/tailscale"
cp "$SRC_DIR/bin/program/tailscaled" "$SRC_DIR/sysroot/usr/local/bin/tailscaled"
chmod 755 "$SRC_DIR/sysroot/usr/local/bin/tailscale" "$SRC_DIR/sysroot/usr/local/bin/tailscaled"

# Copy systemd files if present in official release
if [[ -d "$EXTRACT_DIR/systemd" ]]; then
    cp "$EXTRACT_DIR/systemd/tailscaled.service" "$SRC_DIR/bin/program/systemd/" 2>/dev/null || true
    cp "$EXTRACT_DIR/systemd/tailscaled.defaults" "$SRC_DIR/bin/program/systemd/" 2>/dev/null || true
fi

# Update version files
update_version_file "$VERSION"
update_service_script "$VERSION"
python3 - "$SRC_DIR/config.ini" "$VERSION" <<'PYMETA'
import json, sys
from pathlib import Path
path = Path(sys.argv[1])
config = json.loads(path.read_text())
config["version"] = sys.argv[2] + ".0"
path.write_text(json.dumps(config, indent=2) + "\n")
PYMETA

# Show final checksums
log_info "Installed binary checksums (with TOS watermark):"
shasum -a 256 "$SRC_DIR/bin/program/tailscale" "$SRC_DIR/bin/program/tailscaled"

log_info "Update complete!"
log_info ""
log_info "Next steps:"
log_info "  1. Review changes: git diff src/"
log_info "  2. Build package:  python3 build.py build"
log_info "  3. Verify package: python3 build.py verify dist/*.tpk"
