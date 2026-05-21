#!/usr/bin/env python3
"""
scan_uploads.py
Scans uploads/ for complete file groups (all parts present).

Re-merge logic:
  - If sha256 does NOT exist  → merge as normal
  - If sha256 DOES exist BUT any part file is newer than the sha256
    → a re-upload happened (e.g. failed part replaced) → force re-merge
  - If sha256 exists and all parts are older → already merged, skip
"""

import os
import re
import json
import sys


def scan():
    complete_files = []

    for root, dirs, files in os.walk("uploads"):
        # Don't descend into the merged output folder
        dirs[:] = [d for d in dirs if d != "merged"]
        if "merged" in root.split(os.sep):
            continue

        manifests = [f for f in files if f.endswith(".manifest.txt")]

        for manifest_file in manifests:
            manifest_path = os.path.join(root, manifest_file)
            info = parse_manifest(manifest_path)

            if not info:
                print(f"[SCAN] Could not parse manifest: {manifest_path}")
                continue

            original_name = info["original_name"]
            total_parts   = info["total_parts"]
            safe_base     = info["safe_base"]
            ext            = info["ext"]

            print(f"\n[SCAN] Checking: {original_name}")
            print(f"       Expected parts : {total_parts}")

            # Build the sha256 path
            date_subfolder = root.replace("uploads" + os.sep, "").replace("uploads/", "")
            sha256_path = os.path.join("merged", date_subfolder, original_name + ".sha256")

            # Count parts present
            found_parts = []
            for fname in sorted(files):
                pattern = re.compile(
                    rf"^{re.escape(safe_base)}\.part(\d+)of{total_parts}{re.escape(ext)}$"
                )
                if pattern.match(fname):
                    found_parts.append(os.path.join(root, fname))

            # Sort numerically by part number (fixes part10 > part9 ordering bug)
            def part_num(path):
                m = re.search(r'\.part(\d+)of', os.path.basename(path))
                return int(m.group(1)) if m else 0

            found_parts.sort(key=part_num)
            found   = len(found_parts)
            missing = total_parts - found

            print(f"       Parts found    : {found}/{total_parts}")

            if found != total_parts:
                print(f"       Status: INCOMPLETE — {missing} part(s) still uploading")
                continue

            # ── Re-upload detection ───────────────────────────────────────
            # If sha256 exists, check if any part is newer (= a part was replaced)
            if os.path.exists(sha256_path):
                sha256_mtime = os.path.getmtime(sha256_path)
                newer_parts  = [p for p in found_parts
                                if os.path.getmtime(p) > sha256_mtime]
                if newer_parts:
                    print(f"       Status: RE-UPLOAD DETECTED "
                          f"({len(newer_parts)} part(s) updated) — re-merging")
                    # Remove stale sha256 so the merge job writes a fresh one
                    os.remove(sha256_path)
                else:
                    print(f"       Status: ALREADY MERGED — skipping")
                    continue
            else:
                print(f"       Status: COMPLETE — queuing for validation + merge")

            merged_dest = os.path.join("merged", date_subfolder, original_name)

            complete_files.append({
                "original_name": original_name,
                "total_parts":   total_parts,
                "safe_base":     safe_base,
                "ext":           ext,
                "folder":        root,
                "parts":         found_parts,
                "manifest":      manifest_path,
                "merged_dest":   merged_dest,
            })

    has_complete = len(complete_files) > 0

    print(f"\n[SCAN] Files ready to merge : {len(complete_files)}")

    if not has_complete:
        print("[SCAN] Nothing to do — either still uploading or all already merged.")

    files_json = json.dumps(complete_files)

    # Write outputs for GitHub Actions
    # IMPORTANT: Use heredoc/delimiter syntax for JSON values to avoid
    # shell quoting issues with braces, quotes, and special characters.
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"has_complete={'true' if has_complete else 'false'}\n")
            # Multiline heredoc syntax — safe for any JSON content
            delimiter = "EOF_FILES_JSON"
            f.write(f"files_json<<{delimiter}\n")
            f.write(files_json + "\n")
            f.write(f"{delimiter}\n")
    else:
        print(f"\nhas_complete={has_complete}")
        print(f"files_json={files_json}")


def parse_manifest(path):
    try:
        data = {}
        with open(path, "r") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if ":" in line:
                    key, _, val = line.partition(":")
                    data[key.strip()] = val.strip()

        original_name = data.get("original_name", "")
        if not original_name:
            return None

        total_parts = int(data.get("total_parts", "0"))
        if total_parts == 0:
            return None

        if "." in original_name:
            base = original_name[:original_name.rfind(".")]
            ext  = original_name[original_name.rfind("."):]
        else:
            base = original_name
            ext  = ""

        safe_base = base.replace(" ", "_").replace("(", "").replace(")", "")

        return {
            "original_name": original_name,
            "total_parts":   total_parts,
            "safe_base":     safe_base,
            "ext":           ext,
        }

    except Exception as e:
        print(f"[SCAN] Error parsing {path}: {e}")
        return None


if __name__ == "__main__":
    scan()
