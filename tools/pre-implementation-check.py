#!/usr/bin/env python3
"""pre-implementation-check.py — Session entry gate for Vezir.

Validates that session protocol prerequisites are satisfied before any
implementation work begins. This is a deterministic gate referenced by
CLAUDE.md Session Protocol step 4.

Checks:
  1. docs/ai/handoffs/current.md exists and is non-empty
  2. docs/ai/state/open-items.md exists and is non-empty
  3. docs/ai/STATE.md exists and is non-empty
  4. Active sprint plan.yaml exists (auto-detected from STATE.md)
  5. No active blockers in open-items.md (unless --allow-blockers)
  6. state-sync --check PASS (governed doc consistency)
  7. Previous sprint closure_status=closed (from handoff)

Usage:
    python tools/pre-implementation-check.py
    python tools/pre-implementation-check.py --json
    python tools/pre-implementation-check.py --allow-blockers

Exit codes:
    0 = PASS — session entry gate satisfied
    1 = FAIL — blockers found, fix before implementation
    2 = ERROR — tool failure
"""

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path

# Ensure UTF-8 stdout on Windows
if sys.platform == "win32":
    os.environ.setdefault("PYTHONIOENCODING", "utf-8")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

REPO_ROOT = Path(__file__).parent.parent


@dataclass
class CheckResult:
    """Single check result."""
    name: str
    passed: bool
    message: str


@dataclass
class GateResult:
    """Overall gate result."""
    verdict: str = "PENDING"
    checks: list[CheckResult] = field(default_factory=list)

    def add(self, name: str, passed: bool, message: str) -> None:
        self.checks.append(CheckResult(name=name, passed=passed, message=message))

    @property
    def passed(self) -> bool:
        return all(c.passed for c in self.checks)

    @property
    def fail_count(self) -> int:
        return sum(1 for c in self.checks if not c.passed)


def check_file_exists(path: Path, label: str) -> CheckResult:
    """Check that a file exists and is non-empty."""
    if not path.exists():
        return CheckResult(label, False, f"{path.relative_to(REPO_ROOT)} not found")
    if path.stat().st_size == 0:
        return CheckResult(label, False, f"{path.relative_to(REPO_ROOT)} is empty")
    return CheckResult(label, True, f"{path.relative_to(REPO_ROOT)} exists ({path.stat().st_size} bytes)")


def extract_last_closed_sprint(state_content: str) -> int | None:
    """Extract last closed sprint number from STATE.md."""
    m = re.search(r'Sprint\s+(\d+)\s+closed', state_content)
    if m:
        return int(m.group(1))
    m = re.search(r'[Ss]print\s+(\d+)\s*\|\s*.*\|\s*Closed\s*\|?\s*$', state_content, re.MULTILINE)
    if m:
        return int(m.group(1))
    return None


def extract_next_sprint(state_content: str) -> int | None:
    """Extract next/active sprint from STATE.md phase table."""
    # Look for "Not started" entries in phase status table
    matches = re.findall(r'[Ss](\d+)\s*\|[^|]*\|\s*Not started', state_content)
    if matches:
        return int(matches[0])
    return None


def detect_active_sprint() -> int | None:
    """Detect the active/next sprint from STATE.md."""
    state_path = REPO_ROOT / "docs" / "ai" / "STATE.md"
    if not state_path.exists():
        return None
    content = state_path.read_text(encoding="utf-8")

    # Try next sprint (not started)
    nxt = extract_next_sprint(content)
    if nxt:
        return nxt

    # Fallback: last closed + 1
    last = extract_last_closed_sprint(content)
    if last:
        return last + 1

    return None


def check_active_blockers(open_items_path: Path, allow_blockers: bool) -> CheckResult:
    """Check for active blockers in open-items.md."""
    if not open_items_path.exists():
        return CheckResult("NO_ACTIVE_BLOCKERS", False, "open-items.md not found")

    content = open_items_path.read_text(encoding="utf-8")

    # Find Active Blockers section
    blocker_match = re.search(
        r'##\s*Active\s+Blockers.*?\n(.*?)(?=\n---|\n##|\Z)',
        content,
        re.DOTALL | re.IGNORECASE,
    )
    if not blocker_match:
        return CheckResult("NO_ACTIVE_BLOCKERS", True, "No Active Blockers section found")

    section = blocker_match.group(1).strip()

    # Check if section contains actual blocker rows (not just "none" or empty table)
    has_blockers = bool(re.search(r'\|\s*\d+\s*\|', section))
    if not has_blockers or "*(none)*" in section:
        return CheckResult("NO_ACTIVE_BLOCKERS", True, "No active blockers")

    if allow_blockers:
        return CheckResult("NO_ACTIVE_BLOCKERS", True, "Active blockers present (--allow-blockers)")

    return CheckResult("NO_ACTIVE_BLOCKERS", False, "Active blockers found — resolve before implementation")


def check_previous_sprint_closed(handoff_path: Path) -> CheckResult:
    """Check that the previous sprint is closed per handoff."""
    if not handoff_path.exists():
        return CheckResult("PREV_SPRINT_CLOSED", False, "handoff not found")

    content = handoff_path.read_text(encoding="utf-8")

    # Look for "S{N} closed" or "Sprint {N} closed" or "Last closed sprint: N"
    closed_match = re.search(r'[Ss](?:print\s+)?(\d+)\s*closed', content)
    if closed_match:
        return CheckResult("PREV_SPRINT_CLOSED", True, f"Sprint {closed_match.group(1)} closed")

    # Check for "Last closed sprint: N"
    last_match = re.search(r'Last closed sprint:\s*(\d+)', content)
    if last_match:
        return CheckResult("PREV_SPRINT_CLOSED", True, f"Last closed sprint: {last_match.group(1)}")

    return CheckResult("PREV_SPRINT_CLOSED", False, "Cannot verify previous sprint closure from handoff")


def check_plan_yaml(sprint_num: int | None) -> CheckResult:
    """Check that plan.yaml exists for the active sprint."""
    if sprint_num is None:
        return CheckResult("PLAN_YAML_EXISTS", False, "Could not detect active sprint number")

    plan_path = REPO_ROOT / "docs" / "sprints" / f"sprint-{sprint_num}" / "plan.yaml"
    if not plan_path.exists():
        return CheckResult("PLAN_YAML_EXISTS", False, f"docs/sprints/sprint-{sprint_num}/plan.yaml not found")

    return CheckResult("PLAN_YAML_EXISTS", True, f"plan.yaml exists for sprint {sprint_num}")


def check_state_sync() -> CheckResult:
    """Run state-sync --check and verify PASS."""
    try:
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "tools" / "state-sync.py"), "--check"],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=str(REPO_ROOT),
        )
        if result.returncode == 0:
            return CheckResult("STATE_SYNC_PASS", True, "state-sync --check PASS")
        # Extract failure details
        stderr = result.stderr.strip() or result.stdout.strip()
        fail_lines = [l.strip() for l in stderr.split("\n") if "FAIL" in l]
        detail = fail_lines[0] if fail_lines else "state-sync --check FAIL"
        return CheckResult("STATE_SYNC_PASS", False, detail)
    except subprocess.TimeoutExpired:
        return CheckResult("STATE_SYNC_PASS", False, "state-sync --check timed out (30s)")
    except FileNotFoundError:
        return CheckResult("STATE_SYNC_PASS", False, "state-sync.py not found")


def run_gate(allow_blockers: bool = False) -> GateResult:
    """Run all session entry checks."""
    gate = GateResult()

    handoff_path = REPO_ROOT / "docs" / "ai" / "handoffs" / "current.md"
    open_items_path = REPO_ROOT / "docs" / "ai" / "state" / "open-items.md"
    state_path = REPO_ROOT / "docs" / "ai" / "STATE.md"

    # 1-3. Required files exist
    gate.add(*astuple(check_file_exists(handoff_path, "HANDOFF_EXISTS")))
    gate.add(*astuple(check_file_exists(open_items_path, "OPEN_ITEMS_EXISTS")))
    gate.add(*astuple(check_file_exists(state_path, "STATE_EXISTS")))

    # 4. Active sprint plan.yaml
    sprint_num = detect_active_sprint()
    gate.add(*astuple(check_plan_yaml(sprint_num)))

    # 5. No active blockers
    gate.add(*astuple(check_active_blockers(open_items_path, allow_blockers)))

    # 6. state-sync --check
    gate.add(*astuple(check_state_sync()))

    # 7. Previous sprint closed
    gate.add(*astuple(check_previous_sprint_closed(handoff_path)))

    gate.verdict = "PASS" if gate.passed else "FAIL"
    return gate


def astuple(cr: CheckResult) -> tuple[str, bool, str]:
    """Convert CheckResult to tuple for GateResult.add()."""
    return cr.name, cr.passed, cr.message


def main() -> None:
    parser = argparse.ArgumentParser(description="Session entry gate — pre-implementation check")
    parser.add_argument("--json", action="store_true", help="Output JSON instead of text")
    parser.add_argument("--allow-blockers", action="store_true", help="Allow active blockers (warn only)")
    args = parser.parse_args()

    gate = run_gate(allow_blockers=args.allow_blockers)

    if args.json:
        out = {
            "verdict": gate.verdict,
            "checks": [asdict(c) for c in gate.checks],
        }
        print(json.dumps(out, indent=2))
    else:
        print("=== Pre-Implementation Check ===\n")
        for c in gate.checks:
            icon = "[ OK ]" if c.passed else "[FAIL]"
            print(f"  {icon} {c.name}: {c.message}")
        print()
        if gate.passed:
            print(f"VERDICT: PASS — session entry gate satisfied")
            print("Implementation may proceed.")
        else:
            print(f"VERDICT: FAIL — {gate.fail_count} blocker(s) found")
            print("Fix all FAIL items before starting implementation.")

    sys.exit(0 if gate.passed else 1)


if __name__ == "__main__":
    main()
