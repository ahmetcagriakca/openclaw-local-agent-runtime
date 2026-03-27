#!/usr/bin/env python3
"""Update issues.json PR linkage by scanning merged PRs.

Usage: python tools/update-pr-linkage.py docs/sprints/sprint-19/
       python tools/update-pr-linkage.py docs/sprints/sprint-20/

Scans GitHub PRs for [SN-N.M] title patterns and updates the PR field
in the sprint's issues.json.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def gh(*args):
    """Run gh CLI command and return output."""
    cmd = ["gh"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/update-pr-linkage.py <sprint-dir>")
        sys.exit(1)

    sprint_dir = Path(sys.argv[1])
    issues_json_path = sprint_dir / "issues.json"

    if not issues_json_path.exists():
        print(f"FAIL: {issues_json_path} not found")
        sys.exit(1)

    with open(issues_json_path) as f:
        data = json.load(f)

    sprint = data["sprint"]
    print(f"Sprint: {sprint}")
    print(f"Tasks: {len(data['tasks'])}")

    # Fetch all closed/merged PRs
    out, rc = gh("pr", "list", "--state", "merged", "--limit", "100",
                 "--json", "number,title,mergedAt")
    if rc != 0:
        print(f"FAIL: Could not list PRs (gh not available or not authenticated)")
        sys.exit(1)

    prs = json.loads(out) if out else []
    print(f"Merged PRs found: {len(prs)}")

    # Match PRs to tasks by title pattern [SN-N.M]
    pattern = re.compile(rf'\[S{sprint}-([\d]+(?:\.\w+)*)\]')
    updated = 0

    for pr in prs:
        match = pattern.search(pr["title"])
        if match:
            task_id = match.group(1)
            if task_id in data["tasks"]:
                old_pr = data["tasks"][task_id].get("pr")
                new_pr = pr["number"]
                if old_pr != new_pr:
                    data["tasks"][task_id]["pr"] = new_pr
                    print(f"  {task_id}: PR #{new_pr} (was: {old_pr})")
                    updated += 1

    if updated > 0:
        with open(issues_json_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"\nUpdated {updated} PR linkages in {issues_json_path}")
    else:
        print("\nNo updates needed — all PR linkages current.")

    print("DONE")


if __name__ == "__main__":
    main()
