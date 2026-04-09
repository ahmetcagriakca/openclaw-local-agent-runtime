#!/usr/bin/env python3
"""PR Issue Link Gate — D-152.

Validates that implementation PRs have valid task-issue linkage.
Fail-closed: missing or invalid linkage = exit 1.

Usage:
    python tools/pr-issue-link-check.py --pr-title "..." --pr-body "..." [--sprint N]
    python tools/pr-issue-link-check.py --pr-body-file body.txt --pr-title "..."
"""

import argparse
import re
import sys

# Exempt PR title prefixes — these skip task-issue validation
EXEMPT_PREFIXES = (
    "docs:",
    "chore:",
    "ci:",
    "fix:",
    "bootstrap:",
    "merge:",
    "revert:",
)

# Patterns for extracting linkage fields from PR body
TASK_ISSUE_RE = re.compile(r"^-?\s*Task-Issue:\s*#(\d+)", re.MULTILINE)
PARENT_ISSUE_RE = re.compile(r"^-?\s*Parent-Issue:\s*#(\d+)", re.MULTILINE)
SPRINT_RE = re.compile(r"^-?\s*Sprint:\s*(\d+)", re.MULTILINE)
TASK_ID_RE = re.compile(r"^-?\s*Task-ID:\s*(\S+)", re.MULTILINE)
CLOSES_RE = re.compile(r"^-?\s*Closes:\s*#(\d+)", re.MULTILINE)
# Also match GitHub's native "Closes #N" syntax outside the template
CLOSES_NATIVE_RE = re.compile(r"\bCloses\s+#(\d+)", re.MULTILINE | re.IGNORECASE)


def parse_pr_body(body: str) -> dict:
    """Extract linkage fields from PR body."""
    task_issues = TASK_ISSUE_RE.findall(body)
    parent_issues = PARENT_ISSUE_RE.findall(body)
    sprints = SPRINT_RE.findall(body)
    task_ids = TASK_ID_RE.findall(body)
    closes = CLOSES_RE.findall(body)
    closes_native = CLOSES_NATIVE_RE.findall(body)

    # Merge closes from template field and native syntax
    all_closes = list(set(closes + closes_native))

    return {
        "task_issues": [int(x) for x in task_issues],
        "parent_issues": [int(x) for x in parent_issues],
        "sprints": [int(x) for x in sprints],
        "task_ids": task_ids,
        "closes": [int(x) for x in all_closes],
    }


def is_exempt(title: str) -> bool:
    """Check if PR title indicates an exempt category."""
    title_lower = title.strip().lower()
    return any(title_lower.startswith(prefix) for prefix in EXEMPT_PREFIXES)


def validate_linkage(
    title: str,
    body: str,
    expected_sprint: int | None = None,
    expected_parent: int | None = None,
    expected_branch: str | None = None,
    actual_branch: str | None = None,
) -> list[str]:
    """Validate PR linkage. Returns list of error messages (empty = PASS)."""
    errors = []

    # Exempt check
    if is_exempt(title):
        return []

    parsed = parse_pr_body(body)

    # Must have exactly one task issue
    if len(parsed["task_issues"]) == 0:
        errors.append("FAIL: Missing Task-Issue field in PR body")
    elif len(parsed["task_issues"]) > 1:
        errors.append(
            f"FAIL: Multiple Task-Issue references ({parsed['task_issues']}). "
            f"Implementation PR must reference exactly one task issue."
        )

    # Must have Closes line
    if len(parsed["closes"]) == 0:
        errors.append("FAIL: Missing Closes field in PR body")

    # If task issue is present, closes must reference it
    if parsed["task_issues"] and parsed["closes"]:
        task_issue = parsed["task_issues"][0]
        if task_issue not in parsed["closes"]:
            errors.append(
                f"FAIL: Task-Issue #{task_issue} not in Closes list {parsed['closes']}"
            )

    # Sprint check (if expected sprint provided)
    if expected_sprint is not None and parsed["sprints"]:
        pr_sprint = parsed["sprints"][0]
        if pr_sprint != expected_sprint:
            errors.append(
                f"FAIL: Sprint mismatch — PR says {pr_sprint}, expected {expected_sprint}"
            )

    # Parent issue check (if expected parent provided)
    if expected_parent is not None and parsed["parent_issues"]:
        pr_parent = parsed["parent_issues"][0]
        if pr_parent != expected_parent:
            errors.append(
                f"FAIL: Parent-Issue mismatch — PR says #{pr_parent}, expected #{expected_parent}"
            )

    # Branch check (if both provided)
    if expected_branch and actual_branch:
        if actual_branch != expected_branch:
            errors.append(
                f"FAIL: Branch mismatch — PR branch '{actual_branch}', "
                f"expected '{expected_branch}'"
            )

    return errors


def main():
    parser = argparse.ArgumentParser(description="D-152 PR issue-link gate")
    parser.add_argument("--pr-title", required=True, help="PR title")
    parser.add_argument("--pr-body", default="", help="PR body text")
    parser.add_argument("--pr-body-file", help="Read PR body from file")
    parser.add_argument("--sprint", type=int, help="Expected sprint number")
    parser.add_argument("--parent-issue", type=int, help="Expected parent issue")
    parser.add_argument("--expected-branch", help="Expected branch name")
    parser.add_argument("--actual-branch", help="Actual PR head branch")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    body = args.pr_body
    if args.pr_body_file:
        with open(args.pr_body_file) as f:
            body = f.read()

    errors = validate_linkage(
        title=args.pr_title,
        body=body,
        expected_sprint=args.sprint,
        expected_parent=args.parent_issue,
        expected_branch=args.expected_branch,
        actual_branch=args.actual_branch,
    )

    if args.json:
        import json

        result = {
            "title": args.pr_title,
            "exempt": is_exempt(args.pr_title),
            "errors": errors,
            "pass": len(errors) == 0,
            "parsed": parse_pr_body(body),
        }
        print(json.dumps(result, indent=2))
    else:
        if is_exempt(args.pr_title):
            print(f"EXEMPT: '{args.pr_title}' matches exempt prefix")
            print("PASS")
        elif errors:
            for e in errors:
                print(e)
            print(f"\nFAIL: {len(errors)} linkage error(s)")
        else:
            print("PASS: PR issue linkage valid")

    sys.exit(0 if len(errors) == 0 else 1)


if __name__ == "__main__":
    main()
