#!/usr/bin/env python3
"""
validate.py
Validates all complete file groups before merging.
Accepts either a JSON file path or a raw JSON string as argument.
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

        # ── Check 1: every part exists and is non-empty ───────────────────
        for i, part_path in enumerate(parts, 1):
            if not os.path.exists(part_path):
                errors.append(f"Part {i}/{total_parts} MISSING: {os.path.basename(part_path)}")
                continue

            size = os.path.getsize(part_path)
            part_sizes.append(size)

            if size == 0:
                errors.append(f"Part {i}/{total_parts} is EMPTY (0 bytes)")
            elif size < 100:
                warnings.append(f"Part {i}/{total_parts} suspiciously small ({size} bytes)")
            else:
                print(f"  Part {i:>3}/{total_parts}: {os.path.basename(part_path)}"
                      f"  ({fmt(size)})")

        # ── Check 2: non-final parts should all be same size ─────────────
        if len(part_sizes) >= 2:
            non_final = part_sizes[:-1]
            if len(set(non_final)) > 1:
                diff = max(non_final) - min(non_final)
                if diff > 1024:
                    warnings.append(
                        f"Non-final parts have inconsistent sizes "
                        f"(min={fmt(min(non_final))}, max={fmt(max(non_final))})"
                    )

        # ── Check 3: total size vs manifest ──────────────────────────────
        total_bytes = sum(part_sizes)
        print(f"  Total assembled : {fmt(total_bytes)} ({total_bytes:,} bytes)")

        expected_bytes = read_manifest_size(manifest)
        if expected_bytes:
            diff = abs(expected_bytes - total_bytes)
            print(f"  Manifest says   : {fmt(expected_bytes)} ({expected_bytes:,} bytes)")
            print(f"  Difference      : {diff:,} bytes")

            # Tolerance = 1MB to account for float rounding in manifest text
            TOLERANCE = 1 * 1024 * 1024  # 1MB
            if diff > TOLERANCE:
                errors.append(
                    f"Size mismatch too large: "
                    f"manifest={fmt(expected_bytes)}, "
                    f"actual={fmt(total_bytes)}, "
                    f"diff={fmt(diff)}"
                )
            elif diff > 0:
                warnings.append(
                    f"Tiny size difference of {diff:,} bytes "
                    f"— normal float rounding in manifest, file is OK"
                )

        # ── Check 4: part count matches ───────────────────────────────────
        if len(parts) != total_parts:
            errors.append(
                f"Part count mismatch: found {len(parts)}, expected {total_parts}"
            )

        # ── Result ────────────────────────────────────────────────────────
        if errors:
            all_passed = False
            print(f"\n  RESULT: FAILED")
            for e in errors:
                print(f"    ERROR : {e}")
            for w in warnings:
                print(f"    WARN  : {w}")
        else:
            print(f"\n  RESULT: PASSED", end="")
            if warnings:
                print(f" (with {len(warnings)} note(s))")
                for w in warnings:
                    print(f"    NOTE  : {w}")
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


def read_manifest_size(manifest_path: str):
    try:
        with open(manifest_path) as f:
            for line in f:
                line = line.strip()
                if not line.startswith("total_size"):
                    continue
                _, _, val = line.partition(":")
                val = val.strip()
                parts = val.split()
                if len(parts) == 2:
                    num  = float(parts[0])
                    unit = parts[1].upper()
                    multipliers = {
                        "B":  1,
                        "KB": 1024,
                        "MB": 1024 ** 2,
                        "GB": 1024 ** 3,
                    }
                    if unit in multipliers:
                        return int(num * multipliers[unit])
    except Exception as e:
        print(f"  [WARN] Could not read manifest size: {e}")
    return None


def fmt(b: int) -> str:
    if b < 1024:            return f"{b} B"
    if b < 1024 ** 2:       return f"{b / 1024:.1f} KB"
    if b < 1024 ** 3:       return f"{b / 1024 ** 2:.1f} MB"
    return f"{b / 1024 ** 3:.2f} GB"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 validate.py <path_to_files.json | json_string>")
        sys.exit(1)

    arg = sys.argv[1]

    # Accept either a file path or a raw JSON string
    if os.path.isfile(arg):
        with open(arg) as f:
            files_json = f.read().strip()
    else:
        files_json = arg

    validate(files_json)
