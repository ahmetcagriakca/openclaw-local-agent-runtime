#!/usr/bin/env python3
"""Generate review packet for a sprint.

Usage: python tools/generate-review-packet.py 19
       python tools/generate-review-packet.py 20
"""
import json
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("FAIL: PyYAML required. pip install pyyaml")
    sys.exit(1)


def main():
    if len(sys.argv) < 2:
        print("Usage: python tools/generate-review-packet.py <sprint-number>")
        sys.exit(1)

    sprint = sys.argv[1]
    sprint_dir = Path(f"docs/sprints/sprint-{sprint}")
    evidence_dir = Path(f"evidence/sprint-{sprint}")

    if not sprint_dir.is_dir():
        print(f"FAIL: {sprint_dir} not found")
        sys.exit(1)

    lines = [f"# Sprint {sprint} — Review Packet", "", f"**Generated automatically**", ""]

    # Plan.yaml
    plan_path = sprint_dir / "plan.yaml"
    if plan_path.exists():
        with open(plan_path) as f:
            plan = yaml.safe_load(f)
        lines.append(f"## Sprint Metadata")
        lines.append(f"- **Title:** {plan.get('title', 'N/A')}")
        lines.append(f"- **Phase:** {plan.get('phase', 'N/A')}")
        lines.append(f"- **Model:** {plan.get('model', 'N/A')}")
        lines.append("")
    else:
        lines.append("**WARNING:** plan.yaml not found")
        lines.append("")

    # Issues.json
    issues_path = sprint_dir / "issues.json"
    if issues_path.exists():
        with open(issues_path) as f:
            issues = json.load(f)
        lines.append("## Task Status")
        lines.append("")
        lines.append("| Task | Issue | Branch | PR |")
        lines.append("|------|-------|--------|-----|")
        for task_id, info in issues.get("tasks", {}).items():
            issue = f"#{info.get('issue', '?')}" if info.get('issue') else "—"
            branch = f"`{info.get('branch')}`" if info.get('branch') else "exempt"
            pr = f"#{info.get('pr')}" if info.get('pr') else "—"
            lines.append(f"| {task_id} | {issue} | {branch} | {pr} |")
        lines.append("")
    else:
        lines.append("**WARNING:** issues.json not found")
        lines.append("")

    # Evidence inventory
    lines.append("## Evidence Inventory")
    lines.append("")
    if evidence_dir.is_dir():
        evidence_files = sorted(evidence_dir.iterdir())
        lines.append(f"Total files: {len(evidence_files)}")
        lines.append("")
        for f in evidence_files:
            size = f.stat().st_size
            content_preview = ""
            if f.suffix in ('.txt', '.md') and size < 500:
                content_preview = f" — `{f.read_text(encoding='utf-8').strip()[:80]}`"
            lines.append(f"- `{f.name}` ({size} bytes){content_preview}")
        lines.append("")
    else:
        lines.append("**WARNING:** evidence directory not found")
        lines.append("")

    # Sprint docs
    lines.append("## Sprint Documents")
    lines.append("")
    for f in sorted(sprint_dir.iterdir()):
        lines.append(f"- `{f.name}`")
    lines.append("")

    # Validator check
    lines.append("## Validation")
    lines.append("")
    validator_evidence = evidence_dir / "validator-pass.txt"
    if validator_evidence.exists():
        content = validator_evidence.read_text(encoding='utf-8').strip()
        if "PASS" in content:
            lines.append("- [x] plan.yaml ↔ task breakdown: PASS")
        else:
            lines.append("- [ ] plan.yaml ↔ task breakdown: FAIL")
    else:
        lines.append("- [ ] plan.yaml ↔ task breakdown: NOT CHECKED")

    plan_evidence = evidence_dir / "plan-yaml-valid.txt"
    if plan_evidence.exists():
        lines.append("- [x] plan.yaml parse: VALID")
    else:
        lines.append("- [ ] plan.yaml parse: NOT CHECKED")

    print("\n".join(lines))


if __name__ == "__main__":
    main()
