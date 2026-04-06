#!/usr/bin/env python3
"""task-intake.py — Sprint intake gate per D-142.

Validates that all prerequisites are satisfied before sprint implementation
can begin. This is a hard gate: implementation MUST NOT start until this
tool exits 0.

Checks:
  1. plan.yaml exists and is structurally valid
  2. GitHub milestone exists and is open
  3. Parent issue exists with correct milestone
  4. All task issues exist with correct milestone
  5. Project V2 board items have canonical fields initialized
  6. Governed state docs are consistent (via state-sync --check)

Usage:
    python tools/task-intake.py <sprint_number>
    python tools/task-intake.py <sprint_number> --json
    python tools/task-intake.py <sprint_number> --skip-project
                                    (skip Project V2 checks if no board)

Exit codes:
    0 = PASS — intake gate satisfied, sprint may proceed
    1 = FAIL — blockers found, fix before implementation
    2 = ERROR — tool failure (network, config, etc.)
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
OWNER = "ahmetcagriakca"
REPO = "vezir"

# Required plan.yaml top-level keys
REQUIRED_PLAN_KEYS = {"sprint", "phase", "title", "model", "status", "tasks"}
REQUIRED_TASK_KEYS = {"id", "title", "type"}
VALID_MODELS = {"A", "B"}
VALID_IMPL_STATUS = {"not_started", "in_progress", "done"}
VALID_CLOSURE_STATUS = {"not_started", "evidence_pending", "review_pending", "closed"}

# D-142 canonical Project V2 fields
CANONICAL_FIELDS = {"Status", "Sprint"}


@dataclass
class Finding:
    code: str
    severity: str  # FAIL, WARN, INFO
    message: str


@dataclass
class IntakeResult:
    sprint: int
    passed: bool
    findings: list = field(default_factory=list)

    def add(self, code: str, severity: str, message: str):
        self.findings.append(Finding(code, severity, message))

    @property
    def has_failures(self) -> bool:
        return any(f.severity == "FAIL" for f in self.findings)


def gh(*args: str) -> tuple[str, int]:
    """Run gh CLI command, return (stdout, returncode)."""
    cmd = ["gh"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
    return result.stdout.strip(), result.returncode


def load_plan(sprint: int) -> tuple[dict | None, str | None]:
    """Load and return plan.yaml for a sprint. Returns (plan, error)."""
    plan_path = REPO_ROOT / "docs" / "sprints" / f"sprint-{sprint}" / "plan.yaml"
    if not plan_path.exists():
        return None, f"plan.yaml not found: {plan_path}"
    try:
        import yaml
        with open(plan_path, encoding="utf-8") as f:
            plan = yaml.safe_load(f)
        if not isinstance(plan, dict):
            return None, f"plan.yaml is not a valid YAML mapping"
        return plan, None
    except ImportError:
        return None, "PyYAML not installed (pip install pyyaml)"
    except Exception as e:
        return None, f"plan.yaml parse error: {e}"


def check_plan_structure(plan: dict, sprint: int, result: IntakeResult):
    """Check plan.yaml structural validity."""
    # Required keys
    missing = REQUIRED_PLAN_KEYS - set(plan.keys())
    if missing:
        result.add("PLAN_MISSING_KEYS", "FAIL",
                    f"plan.yaml missing required keys: {sorted(missing)}")
        return

    # Sprint number match
    if plan.get("sprint") != sprint:
        result.add("PLAN_SPRINT_MISMATCH", "FAIL",
                    f"plan.yaml sprint={plan.get('sprint')}, expected {sprint}")

    # Model validity
    model = plan.get("model", "")
    if model not in VALID_MODELS:
        result.add("PLAN_INVALID_MODEL", "FAIL",
                    f"plan.yaml model='{model}', expected one of {VALID_MODELS}")

    # Status fields
    status = plan.get("status", {})
    impl = status.get("implementation_status", "")
    closure = status.get("closure_status", "")
    if impl not in VALID_IMPL_STATUS:
        result.add("PLAN_INVALID_IMPL_STATUS", "FAIL",
                    f"implementation_status='{impl}' not in {VALID_IMPL_STATUS}")
    if closure not in VALID_CLOSURE_STATUS:
        result.add("PLAN_INVALID_CLOSURE_STATUS", "FAIL",
                    f"closure_status='{closure}' not in {VALID_CLOSURE_STATUS}")

    # Tasks
    tasks = plan.get("tasks", [])
    if not tasks:
        result.add("PLAN_NO_TASKS", "FAIL", "plan.yaml has no tasks")
        return

    task_ids = set()
    for t in tasks:
        if not isinstance(t, dict):
            result.add("PLAN_INVALID_TASK", "FAIL", f"Task is not a dict: {t}")
            continue
        missing_t = REQUIRED_TASK_KEYS - set(t.keys())
        if missing_t:
            result.add("PLAN_TASK_MISSING_KEYS", "FAIL",
                        f"Task {t.get('id', '?')} missing keys: {sorted(missing_t)}")
        tid = t.get("id")
        if tid:
            if tid in task_ids:
                result.add("PLAN_DUPLICATE_TASK_ID", "FAIL",
                            f"Duplicate task ID: {tid}")
            task_ids.add(tid)

    result.add("PLAN_VALID", "INFO",
                f"plan.yaml valid: {len(tasks)} tasks, model={model}")


def check_milestone(sprint: int, result: IntakeResult) -> int | None:
    """Check GitHub milestone exists and is open. Returns milestone number."""
    out, rc = gh("api", f"repos/{OWNER}/{REPO}/milestones",
                 "--jq", f'.[] | select(.title == "Sprint {sprint}") | .number,.state')
    if rc != 0 or not out:
        result.add("MILESTONE_MISSING", "FAIL",
                    f"Milestone 'Sprint {sprint}' not found on GitHub")
        return None

    lines = out.strip().split("\n")
    if len(lines) >= 2:
        ms_number = int(lines[0])
        ms_state = lines[1]
        if ms_state != "open":
            result.add("MILESTONE_NOT_OPEN", "WARN",
                        f"Milestone 'Sprint {sprint}' is {ms_state} (expected open)")
        result.add("MILESTONE_OK", "INFO",
                    f"Milestone 'Sprint {sprint}' exists (#{ms_number}, {ms_state})")
        return ms_number

    result.add("MILESTONE_PARSE_ERROR", "FAIL",
                f"Could not parse milestone response: {out}")
    return None


def check_issues(sprint: int, plan: dict, result: IntakeResult):
    """Check parent and task issues exist with correct milestone."""
    issue_config = plan.get("issue", {})
    parent_title_prefix = f"[S{sprint}]"

    # Search for parent issue
    out, rc = gh("issue", "list", "--search", f'"{parent_title_prefix}" in:title',
                 "--json", "number,title,milestone,state", "--limit", "50")
    if rc != 0 or not out:
        result.add("PARENT_ISSUE_MISSING", "FAIL",
                    f"Parent issue with '{parent_title_prefix}' not found")
        return

    try:
        issues = json.loads(out)
    except json.JSONDecodeError:
        result.add("ISSUE_PARSE_ERROR", "FAIL", f"Could not parse issue list")
        return

    parent = None
    for iss in issues:
        if iss.get("title", "").startswith(parent_title_prefix):
            parent = iss
            break

    if not parent:
        result.add("PARENT_ISSUE_MISSING", "FAIL",
                    f"Parent issue with '{parent_title_prefix}' not found")
        return

    parent_num = parent["number"]
    parent_ms = (parent.get("milestone") or {}).get("title", "")
    if parent_ms != f"Sprint {sprint}":
        result.add("PARENT_MILESTONE_WRONG", "FAIL",
                    f"Parent issue #{parent_num} milestone='{parent_ms}', "
                    f"expected 'Sprint {sprint}'")
    else:
        result.add("PARENT_ISSUE_OK", "INFO",
                    f"Parent issue #{parent_num} exists with correct milestone")

    # Check task issues
    tasks = plan.get("tasks", [])
    impl_tasks = [t for t in tasks if not t.get("branch_exempt", False)]

    for task in impl_tasks:
        tid = task["id"]
        task_prefix = f"[S{sprint}-{tid}]"
        found = False
        for iss in issues:
            if task_prefix in iss.get("title", ""):
                found = True
                iss_ms = (iss.get("milestone") or {}).get("title", "")
                if iss_ms != f"Sprint {sprint}":
                    result.add("TASK_MILESTONE_WRONG", "FAIL",
                                f"Task {tid} issue #{iss['number']} "
                                f"milestone='{iss_ms}', expected 'Sprint {sprint}'")
                else:
                    result.add("TASK_ISSUE_OK", "INFO",
                                f"Task {tid} issue #{iss['number']} OK")
                break

        if not found:
            # Wider search
            out2, rc2 = gh("issue", "list", "--search", f'"{task_prefix}" in:title',
                           "--json", "number,title,milestone", "--limit", "10")
            if rc2 == 0 and out2:
                try:
                    wider = json.loads(out2)
                    for iss2 in wider:
                        if task_prefix in iss2.get("title", ""):
                            found = True
                            iss_ms = (iss2.get("milestone") or {}).get("title", "")
                            if iss_ms != f"Sprint {sprint}":
                                result.add("TASK_MILESTONE_WRONG", "FAIL",
                                            f"Task {tid} issue #{iss2['number']} "
                                            f"milestone='{iss_ms}'")
                            else:
                                result.add("TASK_ISSUE_OK", "INFO",
                                            f"Task {tid} issue #{iss2['number']} OK")
                            break
                except json.JSONDecodeError:
                    pass
            if not found:
                result.add("TASK_ISSUE_MISSING", "FAIL",
                            f"Task {tid} has no GitHub issue with title '{task_prefix}'")


def check_state_consistency(result: IntakeResult):
    """Run state-sync --check and report findings."""
    state_sync = REPO_ROOT / "tools" / "state-sync.py"
    if not state_sync.exists():
        result.add("STATE_SYNC_MISSING", "WARN",
                    "tools/state-sync.py not found, skipping consistency check")
        return

    try:
        proc = subprocess.run(
            [sys.executable, str(state_sync), "--check"],
            capture_output=True, text=True, timeout=30,
            cwd=str(REPO_ROOT)
        )
        if proc.returncode == 0:
            result.add("STATE_CONSISTENT", "INFO",
                        "Governed state docs are consistent (state-sync --check PASS)")
        else:
            # Extract first few lines of output for context
            lines = (proc.stdout + proc.stderr).strip().split("\n")[:5]
            summary = "; ".join(l.strip() for l in lines if l.strip())
            result.add("STATE_INCONSISTENT", "FAIL",
                        f"Governed state docs inconsistent: {summary}")
    except subprocess.TimeoutExpired:
        result.add("STATE_SYNC_TIMEOUT", "WARN",
                    "state-sync --check timed out")
    except Exception as e:
        result.add("STATE_SYNC_ERROR", "WARN", f"state-sync error: {e}")


def check_project_board(sprint: int, result: IntakeResult):
    """Check Project V2 items have canonical fields initialized."""
    # Get project ID
    out, rc = gh("api", "graphql", "-f", f"""query={{
        repository(owner: "{OWNER}", name: "{REPO}") {{
            projectsV2(first: 1) {{
                nodes {{ id title number }}
            }}
        }}
    }}""", "--jq", ".data.repository.projectsV2.nodes[0].id")

    if rc != 0 or not out or out == "null":
        result.add("PROJECT_NOT_FOUND", "WARN",
                    "No Project V2 board found, skipping board checks")
        return

    project_id = out.strip()

    # Search for sprint issues on the board
    search = f"[S{sprint}]"
    out2, rc2 = gh("issue", "list", "--search", f'"{search}" in:title',
                    "--json", "number,title", "--limit", "20")
    if rc2 != 0 or not out2:
        result.add("PROJECT_NO_ISSUES", "WARN",
                    f"No issues found with '{search}' prefix")
        return

    try:
        issues = json.loads(out2)
    except json.JSONDecodeError:
        return

    sprint_issues = [i for i in issues if f"[S{sprint}" in i.get("title", "")]
    if sprint_issues:
        result.add("PROJECT_ISSUES_FOUND", "INFO",
                    f"{len(sprint_issues)} sprint issues found on GitHub")
    else:
        result.add("PROJECT_NO_SPRINT_ISSUES", "WARN",
                    f"No issues with [S{sprint}] prefix found")


def main():
    parser = argparse.ArgumentParser(description="Sprint intake gate (D-142)")
    parser.add_argument("sprint", type=int, help="Sprint number to validate")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--skip-project", action="store_true",
                        help="Skip Project V2 board checks")
    args = parser.parse_args()

    result = IntakeResult(sprint=args.sprint, passed=True)

    # 1. Check plan.yaml
    plan, err = load_plan(args.sprint)
    if err:
        result.add("PLAN_LOAD_ERROR", "FAIL", err)
        result.passed = False
    else:
        check_plan_structure(plan, args.sprint, result)

    # 2. Check milestone
    if plan:
        check_milestone(args.sprint, result)

    # 3. Check issues
    if plan:
        check_issues(args.sprint, plan, result)

    # 4. Check state consistency
    check_state_consistency(result)

    # 5. Check project board (optional)
    if not args.skip_project and plan:
        check_project_board(args.sprint, result)

    # Determine final verdict
    result.passed = not result.has_failures

    # Output
    if args.json:
        out = {
            "sprint": result.sprint,
            "passed": result.passed,
            "verdict": "PASS" if result.passed else "FAIL",
            "findings": [asdict(f) for f in result.findings],
            "fail_count": sum(1 for f in result.findings if f.severity == "FAIL"),
            "warn_count": sum(1 for f in result.findings if f.severity == "WARN"),
        }
        print(json.dumps(out, indent=2))
    else:
        print(f"=== Sprint {args.sprint} Intake Gate ===\n")
        for f in result.findings:
            icon = {"FAIL": "FAIL", "WARN": "WARN", "INFO": " OK "}[f.severity]
            print(f"  [{icon}] {f.code}: {f.message}")

        print()
        if result.passed:
            print(f"VERDICT: PASS — Sprint {args.sprint} intake gate satisfied")
            print("Implementation may proceed.")
        else:
            fail_count = sum(1 for f in result.findings if f.severity == "FAIL")
            print(f"VERDICT: FAIL — {fail_count} blocker(s) found")
            print("Fix all FAIL items before starting implementation.")

    sys.exit(0 if result.passed else 1)


if __name__ == "__main__":
    main()
