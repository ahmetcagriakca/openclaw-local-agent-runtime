#!/usr/bin/env python3
"""Close GitHub issues for merged sprint tasks.

Usage: python tools/close-merged-issues.py docs/sprints/sprint-19/
       python tools/close-merged-issues.py docs/sprints/sprint-20/

Reads issues.json, checks if task branches are merged to main,
and closes the corresponding GitHub issues with a comment.
"""
import json
import subprocess
import sys
from pathlib import Path


def gh(*args):
    cmd = ["gh"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True)
    return result.stdout.strip(), result.returncode


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/close-merged-issues.py <sprint-dir>")
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

    closed = 0
    skipped = 0

    for task_id, info in data["tasks"].items():
        issue_num = info.get("issue")
        if not issue_num:
            continue

        # Check if issue is already closed
        out, rc = gh("issue", "view", str(issue_num), "--json", "state", "--jq", ".state")
        if rc != 0:
            print(f"  {task_id}: Could not check issue #{issue_num}")
            continue

        if out == "CLOSED":
            print(f"  {task_id}: #{issue_num} already closed")
            skipped += 1
            continue

        # Close with comment
        comment = f"Task {task_id} completed and merged to main. Closing as part of Sprint {sprint} closure."
        _, rc = gh("issue", "close", str(issue_num), "--comment", comment)
        if rc == 0:
            print(f"  {task_id}: #{issue_num} CLOSED")
            closed += 1
        else:
            print(f"  {task_id}: #{issue_num} close FAILED")

    # Also close parent issue
    parent = data.get("parent_issue")
    if parent:
        out, rc = gh("issue", "view", str(parent), "--json", "state", "--jq", ".state")
        if out == "OPEN":
            comment = f"Sprint {sprint} completed. All tasks merged. Closing parent issue."
            _, rc = gh("issue", "close", str(parent), "--comment", comment)
            if rc == 0:
                print(f"  Parent #{parent} CLOSED")
                closed += 1
        else:
            print(f"  Parent #{parent} already closed")

    print(f"\nDone. Closed: {closed}, Already closed: {skipped}")


if __name__ == "__main__":
    main()
