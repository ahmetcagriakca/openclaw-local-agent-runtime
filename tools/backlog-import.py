#!/usr/bin/env python3
"""Backlog import tool — D-122.

Parses BACKLOG.md and creates/updates GitHub issues for each backlog item.
Idempotent: detects existing issues by [B-NNN] title prefix.

Usage: python tools/backlog-import.py [--dry-run]
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

# Find gh CLI
GH = os.environ.get("GH_CLI", "gh")
for candidate in [r"C:\Program Files\GitHub CLI\gh.exe", "/usr/bin/gh", "/usr/local/bin/gh"]:
    if Path(candidate).exists():
        GH = candidate
        break

DRY_RUN = "--dry-run" in sys.argv
BACKLOG_PATH = Path(__file__).resolve().parent.parent / "docs" / "ai" / "BACKLOG.md"

# Priority → label mapping
PRIORITY_LABELS = {
    "P1": "priority:P1",
    "P2": "priority:P2",
    "P3": "priority:P3",
}

# Category → domain label mapping
CATEGORY_LABELS = {
    "Security": "security",
    "Product": "product",
    "Operations": "operations",
    "DevEx": "devex",
    "Cleanup": "cleanup",
}


def parse_backlog(path: Path) -> list[dict]:
    """Parse BACKLOG.md into structured items."""
    content = path.read_text(encoding="utf-8")
    items = []
    current_priority = "P2"
    current_category = ""

    for line in content.splitlines():
        # Detect priority section
        if line.startswith("## P1"):
            current_priority = "P1"
        elif line.startswith("## P2"):
            current_priority = "P2"
        elif line.startswith("## P3"):
            current_priority = "P3"

        # Detect category from section header
        for cat in CATEGORY_LABELS:
            if cat in line and line.startswith("## "):
                current_category = cat

        # Parse table rows: | B-NNN | Item | Category | Notes |
        match = re.match(r'\|\s*(B-\d+)\s*\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*(.*?)\s*\|', line)
        if match:
            item_id = match.group(1)
            title = match.group(2).strip()
            category = match.group(3).strip()
            notes = match.group(4).strip()

            items.append({
                "id": item_id,
                "title": title,
                "category": category,
                "notes": notes,
                "priority": current_priority,
            })

    return items


def get_existing_issues() -> dict[str, int]:
    """Get existing backlog issues by [B-NNN] prefix."""
    result = subprocess.run(
        [GH, "issue", "list", "--label", "backlog", "--state", "all",
         "--json", "number,title", "--limit", "200"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"WARN: Could not list existing issues: {result.stderr}")
        return {}

    existing = {}
    for issue in json.loads(result.stdout):
        match = re.match(r'\[(B-\d+)\]', issue["title"])
        if match:
            existing[match.group(1)] = issue["number"]
    return existing


def create_issue(item: dict) -> int | None:
    """Create a GitHub issue for a backlog item."""
    title = f"[{item['id']}] {item['title']}"
    body = f"""## Backlog Item

**ID:** {item['id']}
**Category:** {item['category']}
**Priority:** {item['priority']}

{item['notes'] if item['notes'] else 'No additional notes.'}

---
*Auto-imported from BACKLOG.md by backlog-import.py (D-122)*
"""
    labels = ["backlog", PRIORITY_LABELS.get(item["priority"], "priority:P2")]
    domain = CATEGORY_LABELS.get(item["category"])
    if domain:
        labels.append(domain)

    if DRY_RUN:
        print(f"  DRY RUN: Would create: {title} (labels: {labels})")
        return None

    cmd = [GH, "issue", "create", "--title", title, "--body", body]
    for label in labels:
        cmd.extend(["--label", label])

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"  ERROR: {result.stderr.strip()}")
        return None

    # Extract issue number from URL
    url = result.stdout.strip()
    match = re.search(r'/issues/(\d+)', url)
    return int(match.group(1)) if match else None


def main():
    if not BACKLOG_PATH.exists():
        print(f"ERROR: {BACKLOG_PATH} not found")
        sys.exit(1)

    items = parse_backlog(BACKLOG_PATH)
    print(f"Parsed {len(items)} backlog items from BACKLOG.md")
    print(f"Mode: {'DRY RUN' if DRY_RUN else 'LIVE'}")
    print()

    existing = get_existing_issues()
    print(f"Found {len(existing)} existing backlog issues on GitHub")
    print()

    created = 0
    skipped = 0
    errors = 0

    for item in items:
        if item["id"] in existing:
            print(f"  SKIP: {item['id']} — already exists as #{existing[item['id']]}")
            skipped += 1
            continue

        print(f"  CREATE: [{item['id']}] {item['title']} ({item['priority']})")
        issue_num = create_issue(item)
        if issue_num:
            print(f"    -> #{issue_num}")
            created += 1
        elif DRY_RUN:
            created += 1
        else:
            errors += 1

    print()
    print(f"Summary: {created} created, {skipped} skipped, {errors} errors")
    print(f"Total backlog issues on GitHub: {len(existing) + created}")


if __name__ == "__main__":
    main()
