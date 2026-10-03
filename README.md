# Tailscale TPK Builder (TOS5)

Build and manage TerraMaster TOS5 packages for Tailscale.

## Quick Start

```bash
# Install dependencies
uv sync

# Download Tailscale binaries
./update_tailscale.sh latest

# Build package
make build

# Verify package
make verify
```

## Project Structure

```
tailscale-tpk-builder/
├── build.py              # Main build script
├── extract.py            # Extract existing TPK for inspection
├── update_tailscale.sh   # Update Tailscale binaries from official release
├── Makefile              # Build automation
├── pyproject.toml        # Python project config (uv, ruff, mypy)
├── src/                  # Package source files
│   ├── bin/program/      # Tailscale binaries (downloaded separately)
│   ├── functions/        # TOS helper scripts
│   ├── init.d/           # Service scripts
│   ├── images/           # Icons
│   ├── webui/            # Web UI source (PHP, JS, CSS - customizable)
│   ├── config.ini        # Package metadata
│   ├── Tailscale.lang    # Localization
│   └── version           # Version file
└── dist/                 # Built packages
```

## Setup

### Prerequisites

- Python 3.11+
- [uv](https://github.com/astral-sh/uv) (Python package manager)
- curl (for downloading Tailscale)

### Installation

```bash
# Clone the repository
git clone <repo-url>
cd tailscale-tpk-builder

# Install Python dependencies
uv sync

# Download Tailscale binaries (required before first build)
./update_tailscale.sh latest
```

## Usage

### Update Tailscale Version

```bash
# Update to latest stable version
./update_tailscale.sh latest

# Update to specific version
./update_tailscale.sh 1.94.0

# Or use make
make update-latest
make update VERSION=1.94.0
```

The update script will:

1. Download official binaries from `pkgs.tailscale.com`
2. Verify the binaries
3. Add the "TOS" watermark to ELF header
4. Update version files

### Build Package

```bash
# Build with make (recommended)
make build

# Or directly with Python
uv run python build.py build

# Build with custom output
uv run python build.py build -o dist/custom-name.tpk

# Build for ARM64
uv run python build.py build --platform aarch64
```

### Verify Package

```bash
# Verify built package
make verify

# Compare with reference package
uv run python build.py verify dist/*.tpk --reference original.tpk
```

### Extract Existing Package

```bash
# Extract for inspection
uv run python extract.py package.tpk output_dir/

# Verbose mode (shows all files)
uv run python extract.py -v package.tpk output_dir/
```

## Development

### Code Quality

```bash
# Run all checks
make check

# Lint only
make lint

# Type check only
make typecheck

# Format code
make format
```

### Available Make Targets

```bash
make help
```

| Target          | Description                        |
| --------------- | ---------------------------------- |
| `build`         | Build the TPK package              |
| `clean`         | Remove built packages              |
| `verify`        | Verify the built package           |
| `update-latest` | Update Tailscale to latest version |
| `update`        | Update to specific version         |
| `extract`       | Extract a TPK file                 |
| `lint`          | Run ruff linter                    |
| `format`        | Format code with ruff              |
| `typecheck`     | Run mypy type checker              |
| `check`         | Run all checks                     |

## TPK File Format

The `.tpk` format is a custom TerraMaster package format:

| Offset | Size     | Content                         |
| ------ | -------- | ------------------------------- |
| 0x0000 | 2048     | JSON header (space-padded)      |
| 0x0800 | 8192     | Localization file (null-padded) |
| 0x2800 | variable | XZ-compressed TAR archive       |

The JSON header contains:

- Package metadata (id, version, platform, etc.)
- MD5 hash of the XZ archive section

## Build Reproducibility

The build process aims for reproducibility:

- Deterministic TAR entry ordering
- Fixed timestamps for all entries
- Consistent file permissions

**Note:** XZ compression output may vary slightly between systems due to
different LZMA2 implementations. The decompressed content will be identical.

## Security Notes

The Tailscale binaries in this package are the official releases from
`https://pkgs.tailscale.com/stable/` with a 3-byte "TOS" watermark added
to the ELF header padding (bytes 8-10). This watermark is in unused
reserved space and does not affect functionality.

To verify binaries against official releases:

```bash
# Download official release
curl -LO https://pkgs.tailscale.com/stable/tailscale_VERSION_amd64.tgz
tar xzf tailscale_VERSION_amd64.tgz

# Compare BuildID (should match)
readelf -n tailscale_VERSION_amd64/tailscaled | grep "Build ID"
readelf -n src/bin/program/tailscaled | grep "Build ID"

# Binary diff should show only 3 bytes at offset 8-10
cmp -l tailscale_VERSION_amd64/tailscaled src/bin/program/tailscaled
```

## Automated releases and NAS updates

The `Build Tailscale releases` workflow checks the official stable JSON feed every
six hours and on pushes to `main`. It builds a TOS 5 x86_64 package only when that
version has no published build. Manual dispatch accepts an optional numeric version.
The upstream tarball SHA256 is checked before its binaries enter the package.
Each release contains `tailscale-tos5-x86_64.tpk` and `SHA256SUMS`.

The React UI is built with the committed pnpm lockfile. Python dependencies use
`uv.lock`. CI checks the Python code, update rejection tests, and a complete build.
A monthly status commit keeps GitHub's public-repository scheduled workflow active.
GitHub schedules can be delayed; the NAS installs once a build is published.

### Terminal updates on an existing TOS 5 installation

`scripts/tnas-update.sh` runs on the NAS as root and uses its existing utilities
(including `ter_curl`). It does **not** require a browser session or GitHub token
for a public repository. Set `TAILSCALE_REPO=owner/repository` to select the
repository that publishes your builds.
It is specifically for an already-installed Tailscale app at
`/Volume1/@apps/Tailscale`, not a general TerraMaster package installer.

```bash
# Copy scripts to a persistent directory on the NAS, then:
export TAILSCALE_REPO=owner/repository
bash install-cron.sh

# Check availability without downloading or restarting:
/Volume1/@app-updates/Tailscale/tnas-update.sh --check

# Download and validate without installing:
/Volume1/@app-updates/Tailscale/tnas-update.sh --download-only

# Apply latest build. Run detached because this restarts the VPN carrying SSH:
setsid /Volume1/@app-updates/Tailscale/tnas-update.sh --update \
  >> /Volume1/@app-updates/Tailscale/update.log 2>&1 < /dev/null &
```

The installer preserves the existing root crontab and adds a daily check
**in the NAS's configured system timezone**. Override the generic schedule with
`TAILSCALE_UPDATE_SCHEDULE` when installing. It compares the running binary
version rather than package metadata, prevents overlapping updates with a lock,
and refuses automatic downgrades.

### What a scheduled update is allowed to change

Only `bin/program/tailscale` and `bin/program/tailscaled` are replaced. The updater
reads those two regular archive members directly; it never extracts or installs
package service scripts, PHP/JavaScript, settings, metadata, or symlinks.
It downloads the same version's official tarball independently from
`pkgs.tailscale.com`, validates Tailscale's published SHA256, and compares **both
entire executables byte-for-byte**, allowing exactly the builder's three-byte TOS
marker at ELF offsets 8–10. A checksum supplied by this GitHub repository alone
cannot authorize a modified executable. Neither packaged executable is run until
that independent comparison succeeds.

The two old binaries are backed up before stopping the daemon. The updater retains
its exact process arguments, restarts it directly, and checks that it reconnects
with the same Tailscale IP. Failed replacement or health checks restore the previous
binaries. Settings, preferences, identity, custom UI, and system DNS are preserved.
Binary backups live under `/Volume1/@app-updates/Tailscale/backups/` and are not
automatically deleted. Native App Center package metadata remains the original
installed package version; use `tailscale version` for the actual runtime version.
The current service template also reports the real binary version to the custom UI.

This verifies upstream authenticity through HTTPS to Tailscale's official host;
it is not a cryptographic signature or protection against compromise of Tailscale
itself. The NAS keeps a locally installed updater; it does not automatically fetch
new updater code from GitHub. Updating this script is a separate, deliberate step.

Logs: `/Volume1/@app-updates/Tailscale/update.log`.

### Manual rollback

From a local-network SSH connection, stop the daemon, copy `tailscale` and
`tailscaled` from the directory recorded in
`/Volume1/@app-updates/Tailscale/last-backup` into
`/Volume1/@apps/Tailscale/bin/program/`, and restart `/etc/init.d/Tailscale`.
Use a detached command when connecting through Tailscale, because restarting the
daemon interrupts that connection. Preserve the external config directory.

### TOS 5 DNS compatibility

The service template leaves DNS to Tailscale's stored `--accept-dns` preference.
Older versions rewrote `/etc/resolv.conf` to a systemd-resolved stub that TOS 5
does not provide and used GNU-only sed options. An existing installation of that
older service needs a one-time service repair; scheduled binary updates never
install service-script changes. Back up the old script before repairing it.

### Disable daily updates

Remove the single `tnas-update.sh` line using `crontab -e`. Leave all TerraMaster
system jobs intact. The original crontab is also saved as `crontab.before`.

## License

This build tooling is provided as-is for security research and package
maintenance purposes. Tailscale is a trademark of Tailscale Inc.
