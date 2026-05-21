#!/usr/bin/env python3
"""
scan_uploads.py
Scans the uploads/ folder and finds file groups where ALL parts are present.
Outputs a JSON list of complete files for the merge job to process.
"""

import os
import re
import json
import sys

def scan():
    complete_files = []

    # Walk every date folder under uploads/
    for root, dirs, files in os.walk("uploads"):
        # Skip the merged output folder
        if "merged" in root:
            continue

        # Find all manifest files — one per uploaded file
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
            ext           = info["ext"]

            print(f"\n[SCAN] Checking: {original_name}")
            print(f"       Expected parts: {total_parts}")
            print(f"       Safe base name: {safe_base}")

            # Find all part files for this file
            found_parts = []
            for fname in sorted(files):
                pattern = re.compile(
                    rf"^{re.escape(safe_base)}\.part(\d+)of{total_parts}{re.escape(ext)}$"
                )
                if pattern.match(fname):
                    found_parts.append(os.path.join(root, fname))

            found_parts.sort()  # ensure correct order
            print(f"       Found parts: {len(found_parts)}/{total_parts}")

            if len(found_parts) == total_parts:
                print(f"       Status: COMPLETE ✓")

                # Check if already merged
                merged_path = os.path.join("merged", root.replace("uploads/", ""), original_name)
                if os.path.exists(merged_path):
                    print(f"       Already merged — skipping.")
                    continue

                complete_files.append({
                    "original_name": original_name,
                    "total_parts":   total_parts,
                    "safe_base":     safe_base,
                    "ext":           ext,
                    "folder":        root,
                    "parts":         found_parts,
                    "manifest":      manifest_path,
                    "merged_dest":   merged_path,
                })
            else:
                missing = total_parts - len(found_parts)
                print(f"       Status: INCOMPLETE — {missing} part(s) still missing")

    has_complete = len(complete_files) > 0
    files_json   = json.dumps(complete_files)

    print(f"\n[SCAN] Complete file groups found: {len(complete_files)}")
    print(f"[SCAN] Output: {files_json[:200]}...")

    # Write outputs for GitHub Actions
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        with open(github_output, "a") as f:
            f.write(f"has_complete={'true' if has_complete else 'false'}\n")
            f.write(f"files_json={files_json}\n")
    else:
        print(f"\nfiles_json={files_json}")
        print(f"has_complete={has_complete}")


def parse_manifest(path):
    """Parse a .manifest.txt file and return a dict of its fields."""
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

        # Derive safe_base and ext (same logic as GitService.java)
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
