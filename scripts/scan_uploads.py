#!/usr/bin/env python3
"""
scan_uploads.py — Fixed version
Skips files that were already successfully merged in a previous run
by checking for their .sha256 file in the merged/ folder.

FIX: GitHub Actions GITHUB_OUTPUT requires multiline values (like JSON)
     to use the heredoc delimiter syntax, not a plain single-line write.
     Using a plain f.write(f"key={value}\n") silently truncates or breaks
     JSON payloads that contain quotes/newlines, making downstream jobs
     receive empty or malformed data.
"""

import os
import re
import json
import sys
import uuid


def scan():
    complete_files = []

    for root, dirs, files in os.walk("uploads"):
        if "merged" in root:
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
            ext           = info["ext"]

            print(f"\n[SCAN] Checking: {original_name}")
            print(f"       Expected parts : {total_parts}")

            # ── Skip if already merged successfully ───────────────────────
            date_subfolder = root.replace("uploads/", "").replace("uploads\\", "")
            sha256_path = os.path.join("merged", date_subfolder, original_name + ".sha256")

            if os.path.exists(sha256_path):
                print(f"       Status: ALREADY MERGED — skipping (sha256 exists)")
                print(f"       Proof : {sha256_path}")
                continue

            # ── Count parts present ───────────────────────────────────────
            found_parts = []
            for fname in sorted(files):
                pattern = re.compile(
                    rf"^{re.escape(safe_base)}\.part(\d+)of{total_parts}{re.escape(ext)}$"
                )
                if pattern.match(fname):
                    found_parts.append(os.path.join(root, fname))

            found_parts.sort()
            found   = len(found_parts)
            missing = total_parts - found

            print(f"       Parts found    : {found}/{total_parts}")

            if found == total_parts:
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
            else:
                print(f"       Status: INCOMPLETE — {missing} part(s) still uploading")

    has_complete = len(complete_files) > 0

    print(f"\n[SCAN] Files ready to merge : {len(complete_files)}")

    if not has_complete:
        print("[SCAN] Nothing to do — either still uploading or all already merged.")

    files_json = json.dumps(complete_files)

    # ── Write outputs for GitHub Actions ─────────────────────────────────────
    # CRITICAL FIX: JSON strings contain quotes and can be multi-line.
    # GitHub Actions requires the heredoc delimiter syntax for such values:
    #
    #   key<<DELIMITER
    #   value
    #   DELIMITER
    #
    # Using a plain  f.write(f"key={value}\n")  silently truncates the JSON
    # at the first special character, causing validate/merge jobs to receive
    # empty or broken input and skip execution entirely.
    # ─────────────────────────────────────────────────────────────────────────
    github_output = os.environ.get("GITHUB_OUTPUT", "")
    if github_output:
        delimiter = uuid.uuid4().hex          # unique random delimiter
        with open(github_output, "a") as f:
            # Simple boolean — safe as a plain line
            f.write(f"has_complete={'true' if has_complete else 'false'}\n")
            # JSON payload — MUST use heredoc syntax
            f.write(f"files_json<<{delimiter}\n{files_json}\n{delimiter}\n")
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