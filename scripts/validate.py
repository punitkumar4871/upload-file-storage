#!/usr/bin/env python3
"""
validate.py
Validates every complete file group:
  - All parts exist on disk
  - No part is empty or suspiciously small
  - Part sizes are consistent (no truncated upload)
  - Total assembled size matches manifest
"""

import json
import os
import sys


def validate(files_json: str):
    files = json.loads(files_json)

    if not files:
        print("[VALIDATE] No files to validate.")
        return

    print("=" * 56)
    print("           VALIDATION REPORT")
    print("=" * 56)

    all_passed = True

    for entry in files:
        name        = entry["original_name"]
        parts       = entry["parts"]
        total_parts = entry["total_parts"]
        manifest    = entry["manifest"]

        print(f"\nFile     : {name}")
        print(f"Parts    : {total_parts}")

        errors   = []
        warnings = []
        part_sizes = []

        # ── Check 1: every part file exists and is non-empty ──────────────
        for i, part_path in enumerate(parts, 1):
            if not os.path.exists(part_path):
                errors.append(f"Part {i}/{total_parts} MISSING: {os.path.basename(part_path)}")
                continue

            size = os.path.getsize(part_path)
            part_sizes.append(size)

            if size == 0:
                errors.append(f"Part {i}/{total_parts} is EMPTY (0 bytes)")
            elif size < 100:
                warnings.append(f"Part {i}/{total_parts} is suspiciously small ({size} bytes)")
            else:
                print(f"  Part {i:>3}/{total_parts}: {os.path.basename(part_path)}"
                      f"  ({fmt(size)})")

        # ── Check 2: non-final parts should all be the same size ──────────
        if len(part_sizes) >= 2:
            # All parts except last should be same size (they're fixed 20MB chunks)
            non_final = part_sizes[:-1]
            if len(set(non_final)) > 1:
                min_s = min(non_final)
                max_s = max(non_final)
                diff  = max_s - min_s
                if diff > 1024:   # more than 1KB difference is suspicious
                    warnings.append(
                        f"Non-final parts have inconsistent sizes "
                        f"(min={fmt(min_s)}, max={fmt(max_s)}) — possible truncation"
                    )

        # ── Check 3: total size sanity ────────────────────────────────────
        total_bytes = sum(part_sizes)
        print(f"  Total assembled size: {fmt(total_bytes)}")

        # Compare against manifest if it has size info
        expected_size = read_manifest_size(manifest)
        if expected_size and abs(expected_size - total_bytes) > 1024:
            errors.append(
                f"Size mismatch: manifest says {fmt(expected_size)} "
                f"but parts total {fmt(total_bytes)}"
            )

        # ── Check 4: part count matches manifest ──────────────────────────
        if len(parts) != total_parts:
            errors.append(
                f"Part count mismatch: found {len(parts)}, "
                f"manifest says {total_parts}"
            )

        # ── Results ───────────────────────────────────────────────────────
        if errors:
            all_passed = False
            print(f"\n  RESULT: FAILED")
            for e in errors:
                print(f"    ERROR: {e}")
            for w in warnings:
                print(f"    WARN : {w}")
        else:
            print(f"\n  RESULT: PASSED", end="")
            if warnings:
                print(f" (with {len(warnings)} warning(s))")
                for w in warnings:
                    print(f"    WARN: {w}")
            else:
                print(" — all checks OK")

        print("-" * 56)

    print("\n" + "=" * 56)
    if all_passed:
        print("  OVERALL: ALL FILES VALID — proceeding to merge")
        print("=" * 56)
    else:
        print("  OVERALL: VALIDATION FAILED — merge aborted")
        print("=" * 56)
        sys.exit(1)


def read_manifest_size(manifest_path: str) -> int | None:
    """Parse total_size from manifest. Returns bytes or None."""
    try:
        with open(manifest_path) as f:
            for line in f:
                if line.strip().startswith("total_size"):
                    _, _, val = line.partition(":")
                    val = val.strip()
                    # Parse "231.6 MB" / "50.0 MB" / "500 KB" etc.
                    parts = val.split()
                    if len(parts) == 2:
                        num  = float(parts[0])
                        unit = parts[1].upper()
                        multipliers = {"B": 1, "KB": 1024,
                                       "MB": 1024**2, "GB": 1024**3}
                        return int(num * multipliers.get(unit, 1))
    except Exception:
        pass
    return None


def fmt(b: int) -> str:
    if b < 1024:        return f"{b} B"
    if b < 1024**2:     return f"{b/1024:.1f} KB"
    if b < 1024**3:     return f"{b/1024**2:.1f} MB"
    return f"{b/1024**3:.2f} GB"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate.py '<files_json>'")
        sys.exit(1)
    validate(sys.argv[1])
