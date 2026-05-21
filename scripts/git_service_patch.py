"""
git_service_patch.py

Drop-in patch for your GitService client upload loop.
Replaces the single-attempt commit with a retry loop (up to MAX_RETRIES).
Manifest is pushed ONLY after every part succeeds.

Usage: copy the `push_parts_with_retry` function into your GitService class
       and call it instead of the bare commit loop.
"""

import time

MAX_RETRIES   = 5          # attempts per part before giving up
RETRY_DELAYS  = [2, 5, 10, 20, 30]   # seconds between retries (exponential-ish)


def push_parts_with_retry(self, parts, manifest_path, repo, token):
    """
    Commit each part with retry on transient HTTP errors (502, 503, 429…).
    Pushes the manifest only when every part has committed successfully.
    Returns True on full success, False if any part ultimately fails.
    """
    failed_parts = []

    for idx, (part_path, part_label) in enumerate(parts, 1):
        total = len(parts)
        success = False

        for attempt in range(1, MAX_RETRIES + 1):
            try:
                print(f"[GitService] Part {idx}/{total} ({attempt}/{MAX_RETRIES}) → {part_label}")
                self._commit_file(part_path, part_label, repo, token)   # your existing method
                print(f"[GitService]   committed OK")
                success = True
                break

            except Exception as e:
                http_code = getattr(e, 'status_code', None) or getattr(e, 'code', None)
                # Retry on transient errors only
                transient = http_code in (429, 500, 502, 503, 504) or http_code is None
                if transient and attempt < MAX_RETRIES:
                    delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
                    print(f"[GitService]   HTTP {http_code} — retrying in {delay}s …")
                    time.sleep(delay)
                else:
                    print(f"[GitService]   FAILED permanently: HTTP {http_code}: {e}")
                    failed_parts.append(part_label)
                    break

    if failed_parts:
        print(f"\n[GitService] WARNING: {len(failed_parts)} part(s) failed:")
        for p in failed_parts:
            print(f"  ✗ {p}")
        print("[GitService] Manifest NOT pushed. Re-upload to retry.")
        return False

    # All parts committed — now push the manifest to trigger the workflow
    try:
        print(f"\n[GitService] Pushing manifest …")
        self._commit_file(manifest_path, manifest_path, repo, token)
        print(f"[GitService] Manifest pushed — workflow will trigger.")
        return True
    except Exception as e:
        print(f"[GitService] Manifest push FAILED: {e}")
        print("[GitService] Re-push just the manifest file to trigger the workflow.")
        return False
