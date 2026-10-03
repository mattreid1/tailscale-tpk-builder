#!/usr/bin/env python3
"""
TPK Extractor

Extract TerraMaster .tpk packages for inspection.
"""

import argparse
import hashlib
import json
import lzma
import sys
import tarfile
from io import BytesIO
from pathlib import Path

# TPK format constants
JSON_HEADER_SIZE = 2048
LOCALIZATION_OFFSET = 2048
XZ_ARCHIVE_OFFSET = 10240


def extract_tpk(tpk_path: Path, output_dir: Path, verbose: bool = False) -> bool:
    """
    Extract a TPK package.

    Args:
        tpk_path: Path to the TPK file
        output_dir: Directory to extract to
        verbose: Print detailed information
    """
    print(f"Extracting {tpk_path}")

    with open(tpk_path, "rb") as f:
        data = f.read()

    # Parse JSON header
    json_end = data.find(b"}") + 1
    try:
        header = json.loads(data[:json_end].decode("utf-8"))
        print(f"  Package: {header.get('id')} v{header.get('version')}")
        print(f"  Platform: {header.get('platform')}")
        print(f"  Publisher: {header.get('publisher')}")
    except Exception as e:
        print(f"  Error parsing header: {e}")
        return False

    # Extract localization
    loc_data = data[LOCALIZATION_OFFSET:XZ_ARCHIVE_OFFSET].rstrip(b"\x00")

    # Extract XZ archive
    xz_data = data[XZ_ARCHIVE_OFFSET:]

    # Verify MD5
    calculated_md5 = hashlib.md5(xz_data).hexdigest()
    expected_md5 = header.get("md5", "")
    if calculated_md5 != expected_md5:
        print(f"  Warning: MD5 mismatch (expected {expected_md5}, got {calculated_md5})")

    # Decompress
    print("  Decompressing XZ archive...")
    try:
        tar_data = lzma.decompress(xz_data)
        print(f"  Decompressed: {len(tar_data):,} bytes")
    except Exception as e:
        print(f"  Error decompressing: {e}")
        return False

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save header
    header_file = output_dir / "header.json"
    with open(header_file, "w") as f:
        json.dump(header, f, indent=2)
    print(f"  Saved: {header_file}")

    # Save localization
    lang_file = output_dir / "Tailscale.lang"
    lang_file.write_bytes(loc_data)
    print(f"  Saved: {lang_file}")

    # Extract TAR
    print("  Extracting TAR archive...")
    buffer = BytesIO(tar_data)
    with tarfile.open(fileobj=buffer, mode="r") as tar:
        members = tar.getmembers()
        for member in members:
            if verbose:
                mode_str = oct(member.mode)[2:]
                if member.issym():
                    print(f"    l {mode_str} {member.name} -> {member.linkname}")
                elif member.isdir():
                    print(f"    d {mode_str} {member.name}")
                else:
                    print(f"    f {mode_str} {member.name} ({member.size:,} bytes)")

            # Security check: prevent path traversal
            if member.name.startswith("/") or ".." in member.name:
                print(f"    Skipping unsafe path: {member.name}")
                continue

            tar.extract(member, output_dir)

    print(f"  Extracted {len(members)} entries to {output_dir}")
    return True


def main() -> None:
    parser = argparse.ArgumentParser(description="Extract TPK packages")
    parser.add_argument("tpk", type=Path, help="TPK file to extract")
    parser.add_argument(
        "output",
        type=Path,
        nargs="?",
        default=None,
        help="Output directory (default: tpk filename)",
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="Show detailed extraction info"
    )

    args = parser.parse_args()

    if not args.tpk.exists():
        print(f"Error: TPK file not found: {args.tpk}")
        sys.exit(1)

    output_dir = args.output or Path(args.tpk.stem)

    success = extract_tpk(args.tpk, output_dir, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
