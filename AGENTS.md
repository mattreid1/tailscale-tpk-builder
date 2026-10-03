# AGENTS.md - Project Guide for AI Assistants

## Project Overview

**tailscale-tpk-builder** is a build system for creating TerraMaster TOS5 application packages (.tpk) containing Tailscale VPN. It was reverse-engineered from an existing third-party package to enable security auditing, reproducible builds, and automated updates.

### Purpose

1. **Security & Transparency**: Provide full visibility into what's installed on TerraMaster NAS devices
2. **Automated Updates**: Automatically build new packages when Tailscale releases updates
3. **Reproducibility**: Deterministic builds from auditable source files

### Background

TerraMaster NAS devices run TOS (TerraMaster Operating System), a Linux-based OS with a custom app ecosystem. Third-party apps are distributed as `.tpk` packages. This project packages the official Tailscale binaries for TOS5.

**Note:** TOS5 packages include an `install` binary that TOS6/7 packages don't need (it's built into newer TOS versions).

---

## Toolchain

| Tool                                      | Version | Purpose                                   |
| ----------------------------------------- | ------- | ----------------------------------------- |
| Python                                    | 3.11+   | Build scripts                             |
| [uv](https://github.com/astral-sh/uv)     | latest  | Python package manager (fast, Rust-based) |
| [ruff](https://github.com/astral-sh/ruff) | 0.14+   | Linter and formatter                      |
| [mypy](https://mypy-lang.org/)            | 1.19+   | Static type checker                       |
| GNU Make                                  | any     | Build automation                          |
| XZ Utils                                  | any     | Compression (via Python lzma)             |
| curl                                      | any     | Downloading Tailscale binaries            |

### Why These Tools?

- **uv**: Chosen for speed and reliability. Creates reproducible environments via `uv.lock`
- **ruff**: Single tool for linting + formatting, extremely fast
- **mypy**: Strict type checking ensures correctness in the build scripts

---

## Repository Structure

```
tailscale-tpk-builder/
├── .github/
│   └── workflows/
│       ├── check-release.yml    # Scheduled auto-update (every 6h)
│       ├── ci.yml               # PR/push validation
│       └── manual-release.yml   # Manual version builds
├── src/                         # Package source files
│   ├── bin/
│   │   └── program/
│   │       ├── tailscale        # CLI binary (git-ignored, downloaded)
│   │       ├── tailscaled       # Daemon binary (git-ignored, downloaded)
│   │       └── systemd/         # Service configuration
│   ├── functions/
│   │   └── dependapps.sh        # TOS helper functions
│   ├── init.d/
│   │   └── service              # Service start/stop script
│   ├── images/icons/            # App icon
│   ├── install                  # TOS5 install tool (ELF binary)
│   ├── sysroot/                 # Symlink targets (created in tar)
│   ├── webui/                   # Web UI source files (PHP, JS, CSS)
│   │   ├── *.php                # PHP pages for TOS admin interface
│   │   ├── js/                  # JavaScript libraries (jQuery)
│   │   ├── css/                 # Stylesheets
│   │   ├── lib/                 # PHP libraries
│   │   └── theme/               # Theme assets
│   ├── config.ini               # TOS app metadata
│   ├── INFO                     # File manifest with MD5 hashes (generated)
│   ├── Tailscale.lang           # Localization strings
│   ├── version                  # Package version (e.g., "1.92.1.0")
│   └── webui.bz2                # Web UI archive (generated, git-ignored)
├── dist/                        # Built packages (git-ignored)
├── build.py                     # Main build script
├── extract.py                   # TPK extraction tool
├── update_tailscale.sh          # Binary update script
├── Makefile                     # Build automation
├── pyproject.toml               # Python project config
└── AGENTS.md                    # This file
```

---

## TPK File Format

The `.tpk` format is a custom binary format used by TerraMaster TOS:

### Structure

```
Offset      Size        Content
─────────────────────────────────────────────────────
0x0000      2048        JSON header (space-padded)
0x0800      8192        Localization data (null-padded)
0x2800      variable    XZ-compressed TAR archive
```

### JSON Header (bytes 0-2047)

```json
{
  "id": "Tailscale",
  "md5": "<md5 of XZ section>",
  "version": "1.92.1.0",
  "platform": "x86_64",
  "publisher": "OutkastM",
  "category": "Utilities",
  "low_version": "6.0.420",
  ...
}
```

Key fields:

- `md5`: MD5 hash of the XZ-compressed archive (bytes 0x2800 to EOF)
- `version`: Four-part version (Tailscale uses 3-part, we append `.0`)
- `platform`: `x86_64` or `aarch64`
- `low_version`: Minimum TOS version required

### Localization Section (bytes 2048-10239)

Contains `Tailscale.lang` - an INI-style file with translations:

```ini
[en-us]
name = "Tailscale"
auth = "Tailscale"
descript = "Tailscale lets you easily manage access to private resources..."

[de-de]
name = "Tailscale"
...
```

### XZ Archive (bytes 10240+)

XZ-compressed GNU TAR archive containing all package files.

TAR entry order is significant for reproducibility:

1. INFO
2. Tailscale.lang
3. bin/ (directory hierarchy)
4. config.ini
5. functions/
6. images/
7. init.d/
8. sysroot/ (with symlinks)
9. update/
10. version
11. webui.bz2

---

## Key Files Explained

### `build.py`

Main build script with two commands:

- `build`: Create TPK from src/
- `verify`: Validate TPK structure and checksums

Key functions:

- `create_webui_archive()`: Packs src/webui/ into webui.bz2 (XZ-compressed TAR)
- `create_tar_archive()`: Creates deterministic TAR with fixed timestamps
- `compress_xz()`: XZ compression with CRC64 checksums
- `create_json_header()`: Generates the TPK header JSON
- `generate_info_file()`: Creates INFO manifest with MD5 hashes

### `extract.py`

Extracts TPK packages for inspection:

- Parses JSON header
- Decompresses XZ archive
- Extracts TAR contents
- Saves header.json for analysis

### `update_tailscale.sh`

Downloads official Tailscale binaries and prepares them:

1. Fetches from `https://pkgs.tailscale.com/stable/`
2. Extracts `tailscale` and `tailscaled` binaries
3. Adds "TOS" watermark to ELF header (bytes 8-10)
4. Copies to src/bin/program/
5. Updates version files

The watermark is a 3-byte signature in the ELF padding field (EI_PAD), which doesn't affect binary functionality but identifies TOS-packaged binaries.

### `src/init.d/service`

Bash script for service lifecycle:

- `start`: Launches tailscaled daemon
- `stop`: Graceful shutdown with cleanup
- `reload`: Restart sequence
- `status`: Check if running

Notable behaviors:

- Modifies `/etc/resolv.conf` for Tailscale DNS (MagicDNS)
- Creates config symlinks in `/usr/local/@APP_CONFIG/`
- Uses `start-stop-daemon` for process management

### `src/functions/dependapps.sh`

Shared TOS utility functions:

- Version comparison (`V` function)
- Config folder management
- Volume detection
- User/group creation
- Certificate initialization (downloads CA bundle from curl.se)

---

## GitHub Actions Workflows

### `check-release.yml` (Automatic Updates)

**Trigger**: Cron schedule `0 */6 * * *` (every 6 hours)

**Flow**:

```
1. Read current version from src/version
2. Fetch latest from pkgs.tailscale.com
3. Compare versions
4. If newer:
   a. Download binaries
   b. Build TPK
   c. Verify package
   d. Create GitHub Release
   e. Commit version update
```

**Permissions required**: `contents: write`

### `ci.yml` (Continuous Integration)

**Trigger**: Push or PR to main

**Jobs**:

1. `lint`: ruff + mypy
2. `build`: Full build and verify (depends on lint passing)

### `manual-release.yml` (On-Demand)

**Trigger**: `workflow_dispatch` with version input

**Use case**: Building specific versions, pre-releases, or re-builds

---

## Build Process

### Step-by-step

```bash
# 1. Install dependencies
uv sync

# 2. Download Tailscale binaries
./update_tailscale.sh 1.94.0

# 3. Build package
uv run python build.py build

# 4. Verify
uv run python build.py verify dist/*.tpk
```

### What `build.py build` does:

1. Reads version from `src/version`
2. Creates `webui.bz2` from `src/webui/` directory (XZ-compressed TAR)
3. Generates `INFO` file with MD5 hashes of all files
4. Reads `Tailscale.lang` for localization section
5. Creates TAR archive with deterministic ordering
6. Compresses with XZ (LZMA2, CRC64)
7. Calculates MD5 of compressed data
8. Generates JSON header
9. Assembles final TPK:
   - Header (padded to 2048 bytes)
   - Localization (padded to 10240 bytes)
   - XZ archive

---

## Common Tasks

### Update to new Tailscale version

```bash
./update_tailscale.sh 1.95.0
make build
make verify
git add src/version src/init.d/service src/INFO
git commit -m "Update Tailscale to 1.95.0"
```

### Extract and inspect a TPK

```bash
uv run python extract.py some-package.tpk ./extracted/
ls -la extracted/
cat extracted/header.json
```

### Customize the Web UI

The web interface source files are in `src/webui/`:

```bash
# Edit PHP files
ls src/webui/*.php

# Key files:
# - index.php     : Main dashboard
# - top.php       : Header/navigation
# - 1.php-17.php  : Various UI pages
# - ax/handler.php: AJAX handlers

# After editing, rebuild:
make build
```

The build automatically packs `src/webui/` into `webui.bz2`.

### Run code quality checks

```bash
make check      # Both lint and typecheck
make lint       # Just ruff
make typecheck  # Just mypy
make format     # Auto-fix formatting
```

### Compare built package to original

```bash
uv run python build.py verify dist/built.tpk --reference original.tpk
```

---

## Security Considerations

### Binary Verification

The Tailscale binaries are **official releases** from Tailscale with only a 3-byte modification:

| Offset | Original   | Modified           |
| ------ | ---------- | ------------------ |
| 8-10   | `00 00 00` | `54 4f 53` ("TOS") |

This is in the ELF `EI_PAD` field (reserved/unused). To verify:

```bash
# BuildID should match official release
readelf -n src/bin/program/tailscaled | grep "Build ID"

# Only 3 bytes should differ
cmp -l official/tailscaled src/bin/program/tailscaled
# Output: 9 124 0 / 10 117 0 / 11 123 0
```

### Web UI

The `webui.bz2` contains PHP files for the TOS admin interface. Key security notes:

- Authentication relies on TOS session cookies (`$_COOKIE['userName']`, `$_COOKIE['loginStatus']`)
- Uses `shell_exec()` for service control (hardcoded safe paths)
- No user input is passed to shell commands unsanitized

### init.d/service

- Modifies `/etc/resolv.conf` (expected for VPN DNS)
- Downloads CA certificates from `curl.se` (legitimate)
- No external network calls to unknown hosts

---

## Type Annotations

Both Python scripts use strict mypy typing:

```python
# Example from build.py
TAR_ENTRIES: list[tuple[str, str, int, str | None]] = [...]

def build_tpk(src_dir: Path, output_path: Path, platform: str = "x86_64") -> None:
    ...

def verify_tpk(tpk_path: Path, reference_path: Path | None = None) -> bool:
    ...
```

Mypy is configured with `strict = true` in `pyproject.toml`.

---

## Reproducibility Notes

### What IS reproducible:

- TAR entry ordering
- TAR timestamps (fixed to original package time)
- File permissions
- Symlink targets
- JSON header format

### What may vary:

- XZ compression output (LZMA2 implementations differ slightly)
- Final file size (±5KB typical)

The decompressed TAR content is byte-identical across builds.

---

## Troubleshooting

### "Module not found" errors

```bash
uv sync  # Reinstall dependencies
```

### Build fails with missing binaries

```bash
./update_tailscale.sh $(cat src/version | sed 's/\.0$//')
```

### mypy syntax errors

Check for `# type:` comments that mypy interprets as type annotations. The comment `# type: 'f'` will cause issues; use `# entry_type: 'f'` instead.

### GitHub Actions permissions

Ensure repository settings have:

- Actions → General → Read and write permissions
- Allow GitHub Actions to create pull requests

---

## Version Numbering

- **Tailscale**: 3-part semver (`1.92.1`)
- **TPK package**: 4-part (`1.92.1.0`)

The `.0` suffix is appended automatically by `update_tailscale.sh`.

---

## External Resources

- [Tailscale Downloads](https://pkgs.tailscale.com/stable/)
- [Tailscale GitHub](https://github.com/tailscale/tailscale)
- [TerraMaster TOS Documentation](https://www.terra-master.com/)
- [uv Documentation](https://docs.astral.sh/uv/)
- [ruff Documentation](https://docs.astral.sh/ruff/)

## Contribution and privacy rules

- Use Conventional Commits, for example `feat: add package builder` or `fix: verify upstream binaries`.
- Keep hostnames, IP addresses, tailnet names, machine model/kernel details, personal filesystem paths, deployment schedules, logs, credentials, and identity/state files out of commits and public workflow output.
- Document generic installation examples rather than a particular deployed machine.
- `CLAUDE.md` is a symlink to this file; edit `AGENTS.md`.
