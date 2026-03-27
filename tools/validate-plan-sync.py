#!/usr/bin/env python3
"""Validate plan.yaml ↔ task breakdown document sync.

Usage: python tools/validate-plan-sync.py docs/sprints/sprint-19/
"""
import re
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FAIL: PyYAML not installed. Run: pip install pyyaml")
    sys.exit(1)


def extract_plan_tasks(plan_path: Path) -> dict[str, str]:
    """Extract task ID → title mapping from plan.yaml."""
    with open(plan_path) as f:
        data = yaml.safe_load(f)

    if not data or "tasks" not in data:
        print(f"FAIL: No 'tasks' key in {plan_path}")
        sys.exit(1)

    # Check authority block
    authority = data.get("authority", {})
    sot = authority.get("source_of_truth", "")
    if not sot:
        print("WARNING: No source_of_truth declared in authority block")

    return {t["id"]: t["title"] for t in data["tasks"]}


def extract_breakdown_tasks(breakdown_path: Path) -> dict[str, str]:
    """Extract task ID → title mapping from task breakdown markdown."""
    content = breakdown_path.read_text(encoding="utf-8")
    # Match patterns like: **19.1 — title** or **19.G1 — title**
    pattern = r"\*\*(\d+\.\w+)\s*[-—–]\s*(.+?)\*\*"
    matches = re.findall(pattern, content)
    return {tid: title.strip() for tid, title in matches}


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/validate-plan-sync.py <sprint-dir>")
        sys.exit(1)

    sprint_dir = Path(sys.argv[1])
    if not sprint_dir.is_dir():
        print(f"FAIL: Directory not found: {sprint_dir}")
        sys.exit(1)

    # Find plan.yaml
    plan_path = sprint_dir / "plan.yaml"
    if not plan_path.exists():
        print(f"FAIL: plan.yaml not found in {sprint_dir}")
        sys.exit(1)

    # Find task breakdown doc
    breakdown_candidates = list(sprint_dir.glob("*TASK-BREAKDOWN*"))
    if not breakdown_candidates:
        print(f"FAIL: No task breakdown document found in {sprint_dir}")
        sys.exit(1)
    breakdown_path = breakdown_candidates[0]

    print(f"plan.yaml:       {plan_path}")
    print(f"task breakdown:  {breakdown_path}")
    print()

    plan_tasks = extract_plan_tasks(plan_path)
    breakdown_tasks = extract_breakdown_tasks(breakdown_path)

    plan_ids = set(plan_tasks.keys())
    breakdown_ids = set(breakdown_tasks.keys())

    errors = []
    warnings = []

    # Check for IDs in plan but not in breakdown
    only_in_plan = plan_ids - breakdown_ids
    if only_in_plan:
        errors.append(f"Tasks in plan.yaml but NOT in breakdown: {sorted(only_in_plan)}")

    # Check for IDs in breakdown but not in plan
    only_in_breakdown = breakdown_ids - plan_ids
    if only_in_breakdown:
        errors.append(f"Tasks in breakdown but NOT in plan.yaml: {sorted(only_in_breakdown)}")

    # Check title alignment for common IDs
    common_ids = plan_ids & breakdown_ids
    for tid in sorted(common_ids):
        pt = plan_tasks[tid].lower().strip()
        bt = breakdown_tasks[tid].lower().strip()
        if pt != bt:
            warnings.append(f"  {tid}: plan='{plan_tasks[tid]}' vs breakdown='{breakdown_tasks[tid]}'")

    # Report
    print(f"Plan tasks:      {len(plan_ids)} ({sorted(plan_ids)})")
    print(f"Breakdown tasks: {len(breakdown_ids)} ({sorted(breakdown_ids)})")
    print(f"Common:          {len(common_ids)}")
    print()

    if warnings:
        print("WARNINGS (title mismatches — non-blocking):")
        for w in warnings:
            print(w)
        print()

    if errors:
        print("ERRORS:")
        for e in errors:
            print(f"  {e}")
        print()
        print("FAIL: plan.yaml and task breakdown are NOT in sync")
        sys.exit(1)
    else:
        print("PASS: plan.yaml and task breakdown are in sync")
        sys.exit(0)


if __name__ == "__main__":
    main()
