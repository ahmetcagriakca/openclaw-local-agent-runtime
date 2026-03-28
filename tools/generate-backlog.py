#!/usr/bin/env python3
"""Generate BACKLOG.md from GitHub issues — D-122.

Queries GitHub issues with 'backlog' label and generates
BACKLOG.md as a read-only report.

Usage: python tools/generate-backlog.py
"""
import json
import os
import subprocess
import sys
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path

# Find gh CLI
GH = "gh"
for candidate in [r"C:\Program Files\GitHub CLI\gh.exe", "/usr/bin/gh", "/usr/local/bin/gh"]:
    if Path(candidate).exists():
        GH = candidate
        break

OUTPUT_PATH = Path(__file__).resolve().parent.parent / "docs" / "ai" / "BACKLOG.md"


def fetch_backlog_issues() -> list[dict]:
    """Fetch all backlog issues from GitHub."""
    result = subprocess.run(
        [GH, "issue", "list", "--label", "backlog", "--state", "all",
         "--json", "number,title,state,labels", "--limit", "200"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print(f"ERROR: {result.stderr}")
        sys.exit(1)

    return json.loads(result.stdout)


def categorize(issues: list[dict]) -> dict[str, dict[str, list[dict]]]:
    """Categorize issues by priority and domain."""
    categories = defaultdict(lambda: defaultdict(list))

    for issue in issues:
        labels = [l["name"] for l in issue.get("labels", [])]

        # Determine priority
        priority = "P2"  # default
        for l in labels:
            if l.startswith("priority:"):
                priority = l.split(":")[1]

        # Determine domain
        domain = "General"
        for l in labels:
            if l in ("security", "product", "operations", "devex", "cleanup"):
                domain = l.capitalize()

        categories[priority][domain].append(issue)

    return categories


def generate_markdown(categories: dict) -> str:
    """Generate BACKLOG.md content."""
    now = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    lines = [
        "# Backlog -- Vezir Platform",
        "",
        f"**Auto-generated from GitHub issues.** Do not edit directly.",
        f"**Generated:** {now}",
        f"**Source:** `python tools/generate-backlog.py`",
        "",
        "---",
        "",
    ]

    for priority in ["P1", "P2", "P3"]:
        if priority not in categories:
            continue

        domains = categories[priority]
        lines.append(f"## {priority} -- {'High' if priority == 'P1' else 'Medium' if priority == 'P2' else 'Low'} Priority")
        lines.append("")

        for domain in sorted(domains.keys()):
            items = domains[domain]
            lines.append(f"### {domain}")
            lines.append("")
            lines.append("| # | Item | State |")
            lines.append("|---|------|-------|")

            for item in sorted(items, key=lambda x: x["title"]):
                state = "Open" if item["state"] == "OPEN" else "Done"
                lines.append(f"| #{item['number']} | {item['title']} | {state} |")

            lines.append("")

    # Summary
    total = sum(len(items) for domains in categories.values() for items in domains.values())
    open_count = sum(
        1 for domains in categories.values()
        for items in domains.values()
        for item in items
        if item["state"] == "OPEN"
    )
    lines.append("---")
    lines.append("")
    lines.append(f"**Total:** {total} items ({open_count} open)")
    lines.append("")

    return "\n".join(lines)


def main():
    print("Fetching backlog issues from GitHub...")
    issues = fetch_backlog_issues()
    print(f"Found {len(issues)} backlog issues")

    categories = categorize(issues)
    content = generate_markdown(categories)

    OUTPUT_PATH.write_text(content, encoding="utf-8")
    print(f"Generated: {OUTPUT_PATH}")
    print(f"Total: {len(issues)} issues")


if __name__ == "__main__":
    main()
