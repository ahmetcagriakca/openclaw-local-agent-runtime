#!/usr/bin/env python3
"""Check that all sprint branches are merged to main.

Usage: python tools/check-merged-state.py 19
       python tools/check-merged-state.py 20
"""
import subprocess
import sys


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/check-merged-state.py <sprint-number>")
        sys.exit(1)

    sprint = sys.argv[1]
    prefix = f"sprint-{sprint}/"

    # Get all remote branches for this sprint
    result = subprocess.run(
        ["git", "branch", "-r"],
        capture_output=True, text=True
    )
    all_branches = [b.strip() for b in result.stdout.splitlines() if prefix in b]

    # Get merged branches
    result = subprocess.run(
        ["git", "branch", "-r", "--merged", "origin/main"],
        capture_output=True, text=True
    )
    merged_branches = {b.strip() for b in result.stdout.splitlines()}

    print(f"Sprint {sprint} branch check:")
    print(f"  Total remote branches: {len(all_branches)}")

    unmerged = []
    for b in all_branches:
        if b not in merged_branches:
            unmerged.append(b)

    if unmerged:
        print(f"  Unmerged branches: {len(unmerged)}")
        for b in unmerged:
            print(f"    - {b}")
        print()
        print("FAIL: Unmerged sprint branches exist")
        sys.exit(1)
    else:
        print(f"  All {len(all_branches)} branches merged to main")
        print()
        print("PASS: All sprint branches merged")
        sys.exit(0)


if __name__ == "__main__":
    main()
