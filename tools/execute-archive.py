#!/usr/bin/env python3
"""Execute archive manifest — move sprint files to archive directory.

Usage: python tools/execute-archive.py 19
       python tools/execute-archive.py 19 --execute
"""
import json
import subprocess
import sys
from pathlib import Path


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/execute-archive.py <sprint-number> [--execute]")
        sys.exit(1)

    sprint = sys.argv[1]
    execute = "--execute" in sys.argv

    # Generate manifest first
    result = subprocess.run(
        [sys.executable, "tools/generate-archive-manifest.py", sprint],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"FAIL: Could not generate manifest: {result.stderr}")
        sys.exit(1)

    manifest = json.loads(result.stdout)
    moves = manifest.get("moves", [])

    print(f"Archive Execution — Sprint {sprint}")
    print(f"Files to move: {len(moves)}")
    print(f"Mode: {'EXECUTE' if execute else 'DRY RUN'}")
    print()

    moved = 0
    skipped = 0
    errors = 0

    for item in moves:
        src = Path(item["source"])
        dst = Path(item["destination"])

        if not src.exists():
            print(f"  SKIP: {src} (not found)")
            skipped += 1
            continue

        if execute:
            # Create destination directory
            dst.parent.mkdir(parents=True, exist_ok=True)
            # Use git mv for history preservation
            result = subprocess.run(
                ["git", "mv", str(src), str(dst)],
                capture_output=True, text=True
            )
            if result.returncode == 0:
                print(f"  MOVED: {src} → {dst}")
                moved += 1
            else:
                print(f"  ERROR: {src} → {dst}: {result.stderr.strip()}")
                errors += 1
        else:
            print(f"  WOULD MOVE: {src} → {dst}")
            moved += 1

    print()
    print(f"Summary: {moved} moved, {skipped} skipped, {errors} errors")

    if not execute:
        print()
        print("DRY RUN complete. Run with --execute to actually move files.")


if __name__ == "__main__":
    main()
