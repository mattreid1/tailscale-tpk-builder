#!/usr/bin/env python3
"""
Tailscale TPK Builder

Builds a TerraMaster .tpk package from source files.
The TPK format consists of:
  1. JSON header (padded to 2048 bytes)
  2. Localization file content (padded to 10240 bytes)
  3. XZ-compressed TAR archive of package contents
"""

import argparse
import hashlib
import json
import lzma
import shutil
import subprocess
import sys
import tarfile
from io import BytesIO
from pathlib import Path

# TPK format constants
JSON_HEADER_SIZE = 2048
LOCALIZATION_OFFSET = 2048
XZ_ARCHIVE_OFFSET = 10240

# TAR entries with metadata: (name, entry_type, mode, link_target)
# entry_type values: 'f' = file, 'd' = directory, 'l' = symlink
TAR_ENTRIES: list[tuple[str, str, int, str | None]] = [
    ("INFO", "f", 0o755, None),
    ("Tailscale.lang", "f", 0o644, None),
    ("bin/", "d", 0o755, None),
    ("bin/program/", "d", 0o755, None),
    ("bin/program/systemd/", "d", 0o755, None),
    ("bin/program/systemd/tailscaled.defaults", "f", 0o644, None),
    ("bin/program/systemd/tailscaled.service", "f", 0o644, None),
    ("bin/program/tailscaled", "f", 0o755, None),
    ("bin/program/tailscale", "f", 0o755, None),
    ("config.ini", "f", 0o644, None),
    ("functions/", "d", 0o755, None),
    ("functions/dependapps.sh", "f", 0o744, None),
    ("images/", "d", 0o755, None),
    ("images/icons/", "d", 0o755, None),
    ("images/icons/Tailscale.png", "f", 0o644, None),
    ("init.d/", "d", 0o755, None),
    ("init.d/service", "f", 0o755, None),
    ("install", "f", 0o755, None),  # TOS5 install tool
    ("sysroot/", "d", 0o755, None),
    ("sysroot/usr/", "d", 0o755, None),
    ("sysroot/usr/local/", "d", 0o755, None),
    ("sysroot/usr/local/bin/", "d", 0o755, None),
    ("sysroot/usr/local/bin/tailscaled", "l", 0o777, "/usr/local/Tailscale/bin/program/tailscaled"),
    ("sysroot/usr/local/bin/tailscale", "l", 0o777, "/usr/local/Tailscale/bin/program/tailscale"),
    ("sysroot/var/", "d", 0o755, None),
    ("sysroot/var/lib/", "d", 0o755, None),
    ("sysroot/var/lib/tailscale", "l", 0o777, "/usr/local/Tailscale/config"),
    ("update/", "d", 0o755, None),
    ("version", "f", 0o644, None),
    ("webui.bz2", "f", 0o644, None),
]


def get_version_from_source(src_dir: Path) -> str:
    """Read version from the version file."""
    version_file = src_dir / "version"
    if version_file.exists():
        return version_file.read_text().strip()
    return "0.0.0.0"


def build_webui(project_root: Path) -> None:
    """
    Build the React web UI using pnpm.

    The React source is in webui-src/ and builds to src/webui/dist/.
    """
    webui_src = project_root / "webui-src"

    if not webui_src.exists():
        print("  No webui-src/ directory found, skipping React build")
        return

    print("  Building React web UI...")

    # Find pnpm or npm
    pkg_manager = shutil.which("pnpm") or shutil.which("npm")
    if not pkg_manager:
        raise RuntimeError("Neither pnpm nor npm found. Install pnpm: npm install -g pnpm")

    pkg_name = Path(pkg_manager).name
    print(f"    Using {pkg_name}")

    # Install dependencies if node_modules doesn't exist
    node_modules = webui_src / "node_modules"
    if not node_modules.exists():
        print("    Installing dependencies...")
        result = subprocess.run(
            [pkg_manager, "install"],
            cwd=webui_src,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"    ERROR: {pkg_name} install failed:")
            print(result.stderr)
            raise RuntimeError(f"{pkg_name} install failed")

    # Run build
    print("    Running build...")
    result = subprocess.run(
        [pkg_manager, "run", "build"],
        cwd=webui_src,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"    ERROR: {pkg_name} build failed:")
        print(result.stderr)
        raise RuntimeError(f"{pkg_name} build failed")

    print("    React build complete")


def create_webui_archive(src_dir: Path, mtime: int = 1734138336) -> None:
    """
    Create webui.bz2 (XZ-compressed TAR) from the webui/ directory.

    Despite the .bz2 extension, the file is actually XZ compressed (as per TOS convention).

    Args:
        src_dir: Source directory containing webui/ subdirectory
        mtime: Modification time for all entries (default: original package time)
    """
    webui_dir = src_dir / "webui"
    output_path = src_dir / "webui.bz2"

    if not webui_dir.exists():
        raise FileNotFoundError(f"webui directory not found: {webui_dir}")

    print("  Creating webui archive...")

    # Collect all files and directories, sorted for determinism
    entries: list[tuple[str, Path]] = []

    # Add root directory
    entries.append(("./", webui_dir))

    # Walk the directory tree
    for path in sorted(webui_dir.rglob("*")):
        rel_path = "./" + str(path.relative_to(webui_dir))
        if path.is_dir():
            rel_path += "/"
        entries.append((rel_path, path))

    # Sort entries to ensure deterministic order (directories before their contents)
    entries.sort(key=lambda x: x[0])

    # Create TAR archive
    buffer = BytesIO()
    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for rel_path, full_path in entries:
            tarinfo = tarfile.TarInfo(name=rel_path)
            tarinfo.mtime = mtime
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.uname = "root"
            tarinfo.gname = "root"

            if full_path.is_dir():
                tarinfo.type = tarfile.DIRTYPE
                tarinfo.mode = 0o755
                tar.addfile(tarinfo)
            else:
                tarinfo.type = tarfile.REGTYPE
                tarinfo.mode = 0o644
                tarinfo.size = full_path.stat().st_size
                with open(full_path, "rb") as f:
                    tar.addfile(tarinfo, f)

    tar_data = buffer.getvalue()

    # Compress with XZ
    xz_data = compress_xz(tar_data)

    # Write the output
    output_path.write_bytes(xz_data)
    print(f"    webui.bz2: {len(xz_data):,} bytes ({len(tar_data):,} uncompressed)")


def generate_info_file(src_dir: Path) -> str:
    """Generate INFO file with MD5 hashes of all files."""
    lines = []
    for entry, entry_type, _mode, _link_target in TAR_ENTRIES:
        if entry == "INFO":
            continue  # Skip INFO itself
        path = src_dir / entry
        if entry_type == "f":
            if path.exists():
                md5_hash = hashlib.md5(path.read_bytes()).hexdigest()
                lines.append(f"1:file:{entry}:{md5_hash}")
        elif entry_type == "d":
            lines.append(f"1:folder:{entry}:")
        # Symlinks are not included in INFO
    return "\n".join(lines) + "\n"


def create_tar_archive(src_dir: Path, mtime: int = 1734138336) -> bytes:
    """
    Create a TAR archive with deterministic ordering and timestamps.

    Args:
        src_dir: Source directory containing package files
        mtime: Modification time for all entries (default: original package time)
    """
    buffer = BytesIO()

    with tarfile.open(fileobj=buffer, mode="w", format=tarfile.GNU_FORMAT) as tar:
        for entry, entry_type, mode, link_target in TAR_ENTRIES:
            tarinfo = tarfile.TarInfo(name=entry)
            tarinfo.uid = 0
            tarinfo.gid = 0
            tarinfo.uname = "root"
            tarinfo.gname = "root"
            tarinfo.mtime = mtime
            tarinfo.mode = mode

            if entry_type == "d":
                tarinfo.type = tarfile.DIRTYPE
                tar.addfile(tarinfo)

            elif entry_type == "l":
                tarinfo.type = tarfile.SYMTYPE
                tarinfo.linkname = link_target if link_target else ""
                tar.addfile(tarinfo)

            elif entry_type == "f":
                path = src_dir / entry
                if not path.exists():
                    print(f"Warning: {entry} not found, skipping")
                    continue
                tarinfo.size = path.stat().st_size
                with open(path, "rb") as f:
                    tar.addfile(tarinfo, f)

    return buffer.getvalue()


def compress_xz(data: bytes, preset: int = 6) -> bytes:
    """Compress data using XZ/LZMA2."""
    return lzma.compress(data, format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=preset)


def create_json_header(version: str, md5_hash: str, platform: str = "x86_64") -> bytes:
    """Create the JSON header for the TPK file (TOS5 format)."""
    header = {
        "id": "Tailscale",
        "md5": md5_hash,
        "icon": "/images/icons/Tailscale.png",
        "path": "/Tailscale/",
        "name": "",
        "publisher": "OutkastM",
        "exec": True,
        "open_path": False,
        "resize": True,
        "maxmin": True,
        "state": False,
        "type": "iframe",
        "help": "https://tmnascommunity.eu/download/Tailscale",
        "version": version,
        "recommend": False,
        "beta": False,
        "category": "Utilities",
        "depend": [],
        "relation": ["", ""],
        "platform": platform,
        "low_version": "5.1.12",
        "reset": False,
        "official": "/Tailscale/",
    }

    # Compact JSON with specific key order (matching original)
    json_str = json.dumps(header, separators=(",", ":"))
    return json_str.encode("utf-8")


def build_tpk(
    src_dir: Path, output_path: Path, platform: str = "x86_64", project_root: Path | None = None
) -> None:
    """
    Build a TPK package from source files.

    Args:
        src_dir: Directory containing package source files
        output_path: Output path for the .tpk file
        platform: Target platform (x86_64 or aarch64)
        project_root: Project root directory (for finding webui-src/)
    """
    print(f"Building TPK from {src_dir}")

    # Read version
    version = get_version_from_source(src_dir)
    print(f"  Version: {version}")

    # Build React web UI (if webui-src/ exists)
    if project_root is None:
        project_root = src_dir.parent
    build_webui(project_root)

    # Create webui.bz2 from webui/ directory
    create_webui_archive(src_dir)

    # Update INFO file
    print("  Generating INFO file...")
    info_content = generate_info_file(src_dir)
    (src_dir / "INFO").write_text(info_content)

    # Read localization file
    print("  Reading localization...")
    lang_file = src_dir / "Tailscale.lang"
    localization = lang_file.read_bytes()

    # Create TAR archive
    print("  Creating TAR archive...")
    tar_data = create_tar_archive(src_dir)
    print(f"    TAR size: {len(tar_data):,} bytes")

    # Compress with XZ
    print("  Compressing with XZ...")
    xz_data = compress_xz(tar_data)
    print(f"    XZ size: {len(xz_data):,} bytes")

    # Calculate MD5 of XZ data
    md5_hash = hashlib.md5(xz_data).hexdigest()
    print(f"    MD5: {md5_hash}")

    # Create JSON header
    json_header = create_json_header(version, md5_hash, platform)

    # Assemble the TPK file
    print("  Assembling TPK...")
    with open(output_path, "wb") as f:
        # Section 1: JSON header padded to 2048 bytes
        f.write(json_header)
        f.write(b" " * (JSON_HEADER_SIZE - len(json_header)))

        # Section 2: Localization padded to offset 10240
        f.write(localization)
        padding_needed = XZ_ARCHIVE_OFFSET - LOCALIZATION_OFFSET - len(localization)
        f.write(b"\x00" * padding_needed)

        # Section 3: XZ compressed archive
        f.write(xz_data)

    final_size = output_path.stat().st_size
    print(f"  Output: {output_path}")
    print(f"  Size: {final_size:,} bytes")

    # Calculate final checksum
    final_md5 = hashlib.md5(output_path.read_bytes()).hexdigest()
    final_sha256 = hashlib.sha256(output_path.read_bytes()).hexdigest()
    print(f"  MD5: {final_md5}")
    print(f"  SHA256: {final_sha256}")


def verify_tpk(tpk_path: Path, reference_path: Path | None = None) -> bool:
    """
    Verify a built TPK file.

    Args:
        tpk_path: Path to the TPK file to verify
        reference_path: Optional path to reference TPK for comparison
    """
    print(f"Verifying {tpk_path}")

    with open(tpk_path, "rb") as f:
        data = f.read()

    # Check structure
    if len(data) < XZ_ARCHIVE_OFFSET:
        print("  ERROR: File too small")
        return False

    # Verify XZ signature
    if data[XZ_ARCHIVE_OFFSET : XZ_ARCHIVE_OFFSET + 6] != b"\xfd7zXZ\x00":
        print("  ERROR: Invalid XZ signature")
        return False
    print("  XZ signature: OK")

    # Verify JSON header
    try:
        json_end = data.find(b"}") + 1
        header = json.loads(data[:json_end].decode("utf-8"))
        print(f"  JSON header: OK (version {header.get('version')})")
    except Exception as e:
        print(f"  ERROR: Invalid JSON header: {e}")
        return False

    # Verify MD5 matches XZ content
    xz_data = data[XZ_ARCHIVE_OFFSET:]
    calculated_md5 = hashlib.md5(xz_data).hexdigest()
    if calculated_md5 != header.get("md5"):
        print(f"  ERROR: MD5 mismatch (expected {header.get('md5')}, got {calculated_md5})")
        return False
    print("  MD5 verification: OK")

    # Try to decompress and extract
    try:
        decompressed = lzma.decompress(xz_data)
        print(f"  Decompression: OK ({len(decompressed):,} bytes)")
    except Exception as e:
        print(f"  ERROR: Decompression failed: {e}")
        return False

    if reference_path and reference_path.exists():
        ref_data = reference_path.read_bytes()
        if data == ref_data:
            print("  Reference comparison: EXACT MATCH")
        else:
            print(f"  Reference comparison: DIFFERS (built: {len(data)}, ref: {len(ref_data)})")
            # Find first difference
            for i, (a, b) in enumerate(zip(data, ref_data, strict=False)):
                if a != b:
                    print(f"    First difference at offset {i} (0x{i:x})")
                    break

    print("  Verification: PASSED")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Tailscale TPK packages")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # Build command
    build_parser = subparsers.add_parser("build", help="Build a TPK package")
    build_parser.add_argument(
        "--src", type=Path, default=Path("src"), help="Source directory (default: src)"
    )
    build_parser.add_argument("--output", "-o", type=Path, help="Output TPK file path")
    build_parser.add_argument(
        "--platform", choices=["x86_64", "aarch64"], default="x86_64", help="Target platform"
    )

    # Verify command
    verify_parser = subparsers.add_parser("verify", help="Verify a TPK package")
    verify_parser.add_argument("tpk", type=Path, help="TPK file to verify")
    verify_parser.add_argument("--reference", "-r", type=Path, help="Reference TPK for comparison")

    args = parser.parse_args()

    if args.command == "build":
        src_dir = args.src.resolve()
        if not src_dir.exists():
            print(f"Error: Source directory not found: {src_dir}")
            sys.exit(1)

        version = get_version_from_source(src_dir)
        output_path = args.output or Path(
            f"dist/Tailscale TOS5 {version} {args.platform}.tpk"
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        build_tpk(src_dir, output_path, args.platform)

    elif args.command == "verify":
        if not args.tpk.exists():
            print(f"Error: TPK file not found: {args.tpk}")
            sys.exit(1)
        success = verify_tpk(args.tpk, args.reference)
        sys.exit(0 if success else 1)

    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
