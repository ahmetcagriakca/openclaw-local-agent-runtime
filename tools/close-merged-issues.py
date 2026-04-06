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


def is_branch_merged(branch_name: str) -> bool:
    """Check if a branch has been merged into main via git."""
    # Check if the branch ref exists in merged branches
    out, rc = gh("api", f"repos/ahmetcagriakca/vezir/branches/{branch_name}",
                 "--jq", ".name")
    # If branch doesn't exist remotely, check if it was merged (deleted after merge)
    if rc != 0:
        # Branch deleted — check if any merged PR references it
        out2, rc2 = gh("pr", "list", "--state", "merged", "--head", branch_name,
                       "--json", "number", "--jq", "length")
        return rc2 == 0 and out2.strip() not in ("", "0")
    # Branch still exists — check if it's been merged
    out3, rc3 = gh("pr", "list", "--state", "merged", "--head", branch_name,
                   "--json", "number", "--jq", "length")
    return rc3 == 0 and out3.strip() not in ("", "0")


def has_merged_pr(issue_number: int) -> bool:
    """Check if an issue has an associated merged PR (linked or referenced)."""
    # Search for PRs that mention the issue number
    out, rc = gh("pr", "list", "--state", "merged", "--search", f"#{issue_number}",
                 "--json", "number", "--jq", "length")
    if rc == 0 and out.strip() not in ("", "0"):
        return True
    # Also check via issue timeline for linked PRs
    out2, rc2 = gh("api", f"repos/ahmetcagriakca/vezir/issues/{issue_number}/timeline",
                   "--jq", '[.[] | select(.event=="cross-referenced" and .source.issue.pull_request.merged_at != null)] | length')
    return rc2 == 0 and out2.strip() not in ("", "0")


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

    no_merge_evidence = 0
    dry_run = "--dry-run" in sys.argv

    for task_id, info in data["tasks"].items():
        issue_num = info.get("issue")
        if not issue_num:
            continue

        branch_name = info.get("branch")

        # Merge evidence gate: verify branch is merged to main
        if branch_name:
            merged = is_branch_merged(branch_name)
            if not merged:
                print(f"  {task_id}: #{issue_num} SKIPPED — branch '{branch_name}' not merged to main")
                no_merge_evidence += 1
                continue
        else:
            # No branch info — check if there's a merged PR for the issue
            merged_pr = has_merged_pr(issue_num)
            if not merged_pr:
                print(f"  {task_id}: #{issue_num} SKIPPED — no merge evidence (no branch in issues.json, no merged PR)")
                no_merge_evidence += 1
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

        if dry_run:
            print(f"  {task_id}: #{issue_num} WOULD CLOSE (dry-run)")
            continue

        # Close with comment
        comment = f"Task {task_id} completed and merged to main. Closing as part of Sprint {sprint} closure."
        _, rc = gh("issue", "close", str(issue_num), "--comment", comment)
        if rc == 0:
            print(f"  {task_id}: #{issue_num} CLOSED")
            closed += 1
        else:
            print(f"  {task_id}: #{issue_num} close FAILED")

    # Also close parent issue (only if no tasks lack merge evidence)
    parent = data.get("parent_issue")
    if parent and no_merge_evidence == 0:
        out, rc = gh("issue", "view", str(parent), "--json", "state", "--jq", ".state")
        if out == "OPEN":
            if dry_run:
                print(f"  Parent #{parent} WOULD CLOSE (dry-run)")
            else:
                comment = f"Sprint {sprint} completed. All tasks merged. Closing parent issue."
                _, rc = gh("issue", "close", str(parent), "--comment", comment)
                if rc == 0:
                    print(f"  Parent #{parent} CLOSED")
                    closed += 1
        else:
            print(f"  Parent #{parent} already closed")
    elif parent and no_merge_evidence > 0:
        print(f"  Parent #{parent} NOT CLOSED — {no_merge_evidence} task(s) lack merge evidence")

    print(f"\nDone. Closed: {closed}, Already closed: {skipped}, No merge evidence: {no_merge_evidence}")
    if no_merge_evidence > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()
