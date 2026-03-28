#!/usr/bin/env python3
"""project-validator.py — Project V2 board validator per D-123/D-124/D-125.

Validates all items on the Vezir Sprint Board against canonical truth contract.
Exit 0 = VALID, Exit 1 = NOT VALID.

Usage:
    python tools/project-validator.py           # human-readable
    python tools/project-validator.py --json    # machine-readable JSON
"""

import json
import re
import subprocess
import sys
from dataclasses import dataclass, field
from typing import Optional

# --- Constants ---
OWNER = "ahmetcagriakca"
PROJECT_NUMBER = 4
CURRENT_CONTRACT_SPRINT = 31  # D-122: full contract starts at S31
TASK_ID_PATTERN = re.compile(r"\[S\d+-\d+\.\w+\]")
# Closed sprints — add new closed sprints here
CLOSED_SPRINTS = set(range(19, 33))  # S19-S32 are closed

# Fail codes per GPT P6
BLANK_STATUS = "BLANK_STATUS"
INVALID_SPRINT_FORMAT = "INVALID_SPRINT_FORMAT"
MISSING_SPRINT = "MISSING_SPRINT"
MISSING_PRIORITY = "MISSING_PRIORITY"
MISSING_TASK_ID = "MISSING_TASK_ID"
LEGACY_MISSING_TASK_ID = "LEGACY_MISSING_TASK_ID"
MISSING_MILESTONE = "MISSING_MILESTONE"
DONE_BUT_OPEN = "DONE_BUT_OPEN"
CLOSED_SPRINT_OPEN_ISSUE = "CLOSED_SPRINT_OPEN_ISSUE"
CLOSED_NOT_DONE = "CLOSED_NOT_DONE"
UNCLASSIFIED = "UNCLASSIFIED"
BACKLOG_CLOSURE_ELIGIBLE = "BACKLOG_CLOSURE_ELIGIBLE"


@dataclass
class Finding:
    code: str
    severity: str  # FAIL, WARN, INFO
    issue_number: int
    title: str
    message: str


@dataclass
class ProjectItem:
    item_id: str
    number: int
    title: str
    state: str  # OPEN / CLOSED
    status: Optional[str]  # Project V2 Status field (Done, In Progress, Todo, etc.)
    sprint: Optional[float]  # Project V2 Sprint number field
    milestone: Optional[str]
    labels: list = field(default_factory=list)
    item_class: str = ""  # Classification result


def run_gh_graphql(query: str) -> dict:
    """Run a GraphQL query via gh CLI."""
    result = subprocess.run(
        ["gh", "api", "graphql", "-f", f"query={query}"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"Error running GraphQL query: {result.stderr}", file=sys.stderr)
        sys.exit(2)
    return json.loads(result.stdout)


def fetch_project_items() -> list[ProjectItem]:
    """Fetch all items from Project V2 board."""
    query = """
    query {
      user(login: "%s") {
        projectV2(number: %d) {
          items(first: 100) {
            nodes {
              id
              content {
                ... on Issue {
                  number
                  title
                  state
                  labels(first: 15) { nodes { name } }
                  milestone { title }
                }
              }
              sprint: fieldValueByName(name: "Sprint") {
                ... on ProjectV2ItemFieldNumberValue { number }
              }
              status: fieldValueByName(name: "Status") {
                ... on ProjectV2ItemFieldSingleSelectValue { name }
              }
            }
          }
        }
      }
    }
    """ % (OWNER, PROJECT_NUMBER)

    data = run_gh_graphql(query)
    items = []
    for node in data["data"]["user"]["projectV2"]["items"]["nodes"]:
        content = node.get("content")
        if not content or "number" not in content:
            continue  # Skip draft items or PRs

        labels = [l["name"] for l in content.get("labels", {}).get("nodes", [])]
        sprint_val = node.get("sprint", {})
        sprint_num = sprint_val.get("number") if sprint_val else None
        status_val = node.get("status", {})
        status_name = status_val.get("name") if status_val else None
        milestone = content.get("milestone", {})
        milestone_title = milestone.get("title") if milestone else None

        items.append(ProjectItem(
            item_id=node["id"],
            number=content["number"],
            title=content["title"],
            state=content["state"],
            status=status_name,
            sprint=sprint_num,
            milestone=milestone_title,
            labels=labels,
        ))
    return items


def classify_item(item: ProjectItem) -> str:
    """Classify item per D-124 taxonomy."""
    has_backlog = "backlog" in item.labels
    has_sprint = "sprint" in item.labels

    if has_backlog and not has_sprint:
        return "backlog"

    if has_sprint:
        sprint_num = item.sprint
        if sprint_num is not None and sprint_num >= CURRENT_CONTRACT_SPRINT:
            return "sprint-task"
        if sprint_num is not None and sprint_num < CURRENT_CONTRACT_SPRINT:
            return "legacy-sprint"
        # Sprint label but no Sprint field — check milestone
        if item.milestone:
            ms_match = re.search(r"(\d+)", item.milestone)
            if ms_match:
                ms_num = int(ms_match.group(1))
                if ms_num >= CURRENT_CONTRACT_SPRINT:
                    return "sprint-task"
                return "legacy-sprint"
        return "sprint-task"  # Sprint label, assume current contract

    if has_backlog and has_sprint:
        # Both labels — treat as backlog (backlog issues delivered via sprint)
        return "backlog"

    return "unclassified"


def validate_item(item: ProjectItem) -> list[Finding]:
    """Validate a single item per D-123/D-125."""
    findings = []

    def add(code, severity, message):
        findings.append(Finding(code, severity, item.number, item.title, message))

    # Universal checks (all items)
    if not item.status:
        add(BLANK_STATUS, "FAIL", "Project Status is blank")

    # State sync checks per D-125
    if item.status == "Done" and item.state == "OPEN":
        add(DONE_BUT_OPEN, "FAIL", "Status=Done but issue is OPEN")
    if item.state == "CLOSED" and item.status and item.status != "Done":
        add(CLOSED_NOT_DONE, "FAIL", f"Issue CLOSED but Status={item.status} (expected Done)")

    # Classification-specific checks
    cls = item.item_class

    if cls == "unclassified":
        add(UNCLASSIFIED, "FAIL", "Cannot classify item — no backlog or sprint label")
        return findings

    if cls == "backlog":
        # Priority label required
        has_priority = any(l.startswith("priority:") for l in item.labels)
        if not has_priority:
            add(MISSING_PRIORITY, "FAIL", "Backlog item missing priority label (priority:P1/P2/P3)")
        # Backlog closure eligibility (INFO)
        if item.state == "CLOSED" and item.status == "Done":
            add(BACKLOG_CLOSURE_ELIGIBLE, "INFO", "Backlog item closed and Done — eligible for archive")

    if cls in ("sprint-task", "legacy-sprint", "normalized-legacy"):
        # Sprint field required
        if item.sprint is None:
            add(MISSING_SPRINT, "FAIL", "Sprint-labeled item has no Sprint field value")
        elif not isinstance(item.sprint, (int, float)) or item.sprint != int(item.sprint):
            add(INVALID_SPRINT_FORMAT, "FAIL", f"Sprint field value '{item.sprint}' is not a valid integer")

        # Closed sprint + open issue check (D-125)
        if item.sprint is not None and int(item.sprint) in CLOSED_SPRINTS and item.state == "OPEN":
            add(CLOSED_SPRINT_OPEN_ISSUE, "FAIL",
                f"Issue OPEN but Sprint {int(item.sprint)} is closed")

        # Task ID check
        has_task_id = bool(TASK_ID_PATTERN.search(item.title))
        if cls == "sprint-task" and not has_task_id:
            add(MISSING_TASK_ID, "FAIL", "Sprint task (S31+) missing [SN-N.M] title pattern")
        elif cls in ("legacy-sprint", "normalized-legacy") and not has_task_id:
            add(LEGACY_MISSING_TASK_ID, "WARN", "Legacy sprint task missing [SN-N.M] title pattern")

        # Milestone check (WARN in v1)
        if not item.milestone:
            add(MISSING_MILESTONE, "WARN", "Sprint task has no milestone assigned")

    return findings


def main():
    json_mode = "--json" in sys.argv

    items = fetch_project_items()
    all_findings: list[Finding] = []

    # Classify all items
    for item in items:
        item.item_class = classify_item(item)

    # Validate all items
    for item in items:
        findings = validate_item(item)
        all_findings.extend(findings)

    # Separate by severity
    fails = [f for f in all_findings if f.severity == "FAIL"]
    warns = [f for f in all_findings if f.severity == "WARN"]
    infos = [f for f in all_findings if f.severity == "INFO"]

    is_valid = len(fails) == 0

    if json_mode:
        output = {
            "valid": is_valid,
            "total_items": len(items),
            "classifications": {},
            "findings": [
                {
                    "code": f.code,
                    "severity": f.severity,
                    "issue": f.issue_number,
                    "title": f.title,
                    "message": f.message,
                }
                for f in all_findings
            ],
            "summary": {
                "fail": len(fails),
                "warn": len(warns),
                "info": len(infos),
            },
            "backlog_closure_eligible": [
                f.issue_number for f in infos if f.code == BACKLOG_CLOSURE_ELIGIBLE
            ],
        }
        # Count classifications
        for item in items:
            cls = item.item_class
            output["classifications"][cls] = output["classifications"].get(cls, 0) + 1

        print(json.dumps(output, indent=2))
    else:
        print(f"=== Project V2 Board Validator ===")
        print(f"Total items: {len(items)}")
        print()

        # Classification summary
        class_counts: dict[str, int] = {}
        for item in items:
            class_counts[item.item_class] = class_counts.get(item.item_class, 0) + 1
        print("Classifications:")
        for cls, count in sorted(class_counts.items()):
            print(f"  {cls}: {count}")
        print()

        if fails:
            print(f"FAILURES ({len(fails)}):")
            for f in fails:
                print(f"  [{f.code}] #{f.issue_number} {f.title}")
                print(f"    {f.message}")
            print()

        if warns:
            print(f"WARNINGS ({len(warns)}):")
            for f in warns:
                print(f"  [{f.code}] #{f.issue_number} {f.title}")
                print(f"    {f.message}")
            print()

        if infos:
            print(f"INFO ({len(infos)}):")
            for f in infos:
                print(f"  [{f.code}] #{f.issue_number} {f.title}")
                print(f"    {f.message}")
            print()

        eligible = [f.issue_number for f in infos if f.code == BACKLOG_CLOSURE_ELIGIBLE]
        if eligible:
            print(f"BACKLOG_CLOSURE_ELIGIBLE: {eligible}")
            print()

        print(f"Summary: {len(fails)} FAIL, {len(warns)} WARN, {len(infos)} INFO")
        if is_valid:
            print("Result: VALID")
        else:
            print("Result: NOT VALID")

    sys.exit(0 if is_valid else 1)


if __name__ == "__main__":
    main()
