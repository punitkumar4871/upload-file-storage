#!/usr/bin/env python3
"""
merge.py
Merges all complete file groups into their original single files.
Output goes into:  merged/uploads/YYYY/MM/DD/<original_filename>

GitHub cannot store the merged file (too large) so it is uploaded
as a GitHub Actions Artifact — downloadable from the Actions tab
for 7 days after the workflow runs.
"""

import json
import os
import sys
import re
import hashlib


def merge_all(files_json: str):
    files = json.loads(files_json)

    if not files:
        print("[MERGE] No complete files to merge.")
        return

    print("=" * 56)
    print("            MERGE REPORT")
    print("=" * 56)

    for entry in files:
        name  = entry["original_name"]
        parts = entry["parts"]   # Already sorted numerically by scan_uploads.py
        dest  = entry["merged_dest"]
        total = entry["total_parts"]

        # Extra safety: re-sort numerically in case list arrived unsorted
        def part_num(path):
            m = re.search(r'\.part(\d+)of', os.path.basename(path))
            return int(m.group(1)) if m else 0

        parts = sorted(parts, key=part_num)

        print(f"\nMerging : {name}")
        print(f"Parts   : {total}")
        print(f"Output  : {dest}")

        # Verify parts are in expected order before merging
        for i, p in enumerate(parts, 1):
            n = part_num(p)
            if n != i:
                print(f"  ERROR: Expected part {i} but got part {n} ({os.path.basename(p)})")
                sys.exit(1)

        # Create destination directory
        os.makedirs(os.path.dirname(dest), exist_ok=True)

        # Remove old merged file if re-running
        if os.path.exists(dest):
            os.remove(dest)

        # SHA256 for integrity verification
        sha = hashlib.sha256()
        total_bytes = 0

        with open(dest, "wb") as out:
            for i, part_path in enumerate(parts, 1):
                part_size = os.path.getsize(part_path)
                print(f"  Adding part {i:>3}/{total}: "
                      f"{os.path.basename(part_path)}  ({fmt(part_size)})")

                with open(part_path, "rb") as p:
                    while True:
                        chunk = p.read(8 * 1024 * 1024)  # read 8MB at a time
                        if not chunk:
                            break
                        out.write(chunk)
                        sha.update(chunk)
                        total_bytes += len(chunk)

        final_size = os.path.getsize(dest)
        checksum   = sha.hexdigest()

        print(f"\n  Final size : {fmt(final_size)}")
        print(f"  SHA256     : {checksum}")

        # Write checksum file next to merged file
        checksum_path = dest + ".sha256"
        with open(checksum_path, "w") as cf:
            cf.write(f"{checksum}  {name}\n")
        print(f"  Checksum   : saved to {checksum_path}")

        print(f"\n  RESULT: MERGED OK")
        print("-" * 56)

    print("\n" + "=" * 56)
    print("  ALL MERGES COMPLETE")
    print("  Files are in: merged/")
    print("  Download them from the Actions tab → Artifacts")
    print("=" * 56)


def fmt(b: int) -> str:
    if b < 1024:        return f"{b} B"
    if b < 1024**2:     return f"{b/1024:.1f} KB"
    if b < 1024**3:     return f"{b/1024**2:.1f} MB"
    return f"{b/1024**3:.2f} GB"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 merge.py '<files_json>'")
        sys.exit(1)
    merge_all(sys.argv[1])
