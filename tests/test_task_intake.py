"""Tests for task-intake.py — D-142 intake gate validation.

T71.2: Comprehensive unit tests for the sprint intake gate tool.
Tests cover plan.yaml validation, milestone checks, issue checks,
state consistency delegation, and project board checks.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

# Add tools/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from importlib import import_module

intake = import_module("task-intake")

IntakeResult = intake.IntakeResult
Finding = intake.Finding
load_plan = intake.load_plan
check_plan_structure = intake.check_plan_structure
check_milestone = intake.check_milestone
check_issues = intake.check_issues
check_state_consistency = intake.check_state_consistency
check_project_board = intake.check_project_board


def make_plan(**overrides):
    """Create a valid plan.yaml dict with optional overrides."""
    plan = {
        "sprint": 71,
        "phase": 9,
        "title": "Test Sprint",
        "model": "A",
        "status": {
            "implementation_status": "not_started",
            "closure_status": "not_started",
        },
        "tasks": [
            {"id": "71.1", "title": "Task one", "type": "implementation"},
            {"id": "71.2", "title": "Task two", "type": "implementation"},
        ],
    }
    plan.update(overrides)
    return plan


def find_code(findings, code):
    """Check if a finding with given code exists in result."""
    return any(f.code == code for f in findings)


def find_severity(findings, code):
    """Get severity for a specific finding code."""
    for f in findings:
        if f.code == code:
            return f.severity
    return None


# --- IntakeResult Tests ---

class TestIntakeResult:
    def test_no_findings_passes(self):
        r = IntakeResult(sprint=71, passed=True)
        assert r.passed
        assert not r.has_failures

    def test_info_finding_no_failure(self):
        r = IntakeResult(sprint=71, passed=True)
        r.add("TEST_OK", "INFO", "All good")
        assert not r.has_failures

    def test_warn_finding_no_failure(self):
        r = IntakeResult(sprint=71, passed=True)
        r.add("TEST_WARN", "WARN", "Minor issue")
        assert not r.has_failures

    def test_fail_finding_triggers_failure(self):
        r = IntakeResult(sprint=71, passed=True)
        r.add("TEST_FAIL", "FAIL", "Blocker found")
        assert r.has_failures

    def test_multiple_findings(self):
        r = IntakeResult(sprint=71, passed=True)
        r.add("A", "INFO", "ok")
        r.add("B", "WARN", "warning")
        r.add("C", "FAIL", "fail")
        assert len(r.findings) == 3
        assert r.has_failures


# --- Plan Structure Tests ---

class TestPlanStructure:
    def test_valid_plan(self):
        result = IntakeResult(sprint=71, passed=True)
        check_plan_structure(make_plan(), 71, result)
        assert find_code(result.findings, "PLAN_VALID")
        assert not result.has_failures

    def test_missing_required_keys(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = {"sprint": 71}  # Missing most keys
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_MISSING_KEYS")
        assert find_severity(result.findings, "PLAN_MISSING_KEYS") == "FAIL"

    def test_sprint_mismatch(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(sprint=70)
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_SPRINT_MISMATCH")

    def test_invalid_model(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(model="C")
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_INVALID_MODEL")

    def test_invalid_impl_status(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(status={"implementation_status": "COMPLETE", "closure_status": "not_started"})
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_INVALID_IMPL_STATUS")

    def test_invalid_closure_status(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(status={"implementation_status": "not_started", "closure_status": "COMPLETE"})
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_INVALID_CLOSURE_STATUS")

    def test_no_tasks(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(tasks=[])
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_NO_TASKS")

    def test_task_missing_keys(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(tasks=[{"id": "71.1"}])  # Missing title, type
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_TASK_MISSING_KEYS")

    def test_duplicate_task_ids(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(tasks=[
            {"id": "71.1", "title": "A", "type": "implementation"},
            {"id": "71.1", "title": "B", "type": "implementation"},
        ])
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_DUPLICATE_TASK_ID")

    def test_invalid_task_not_dict(self):
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(tasks=["not a dict"])
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_INVALID_TASK")

    def test_model_A_valid(self):
        result = IntakeResult(sprint=71, passed=True)
        check_plan_structure(make_plan(model="A"), 71, result)
        assert not result.has_failures

    def test_model_B_valid(self):
        result = IntakeResult(sprint=71, passed=True)
        check_plan_structure(make_plan(model="B"), 71, result)
        assert not result.has_failures


# --- Milestone Tests ---

class TestMilestone:
    def test_milestone_exists_open(self):
        with patch.object(intake, "gh", return_value=("47\nopen", 0)):
            result = IntakeResult(sprint=71, passed=True)
            ms_num = check_milestone(71, result)
            assert ms_num == 47
            assert find_code(result.findings, "MILESTONE_OK")

    def test_milestone_missing(self):
        with patch.object(intake, "gh", return_value=("", 1)):
            result = IntakeResult(sprint=71, passed=True)
            ms_num = check_milestone(71, result)
            assert ms_num is None
            assert find_code(result.findings, "MILESTONE_MISSING")

    def test_milestone_closed_warns(self):
        with patch.object(intake, "gh", return_value=("47\nclosed", 0)):
            result = IntakeResult(sprint=71, passed=True)
            ms_num = check_milestone(71, result)
            assert ms_num == 47
            assert find_code(result.findings, "MILESTONE_NOT_OPEN")
            assert find_severity(result.findings, "MILESTONE_NOT_OPEN") == "WARN"

    def test_milestone_empty_response(self):
        with patch.object(intake, "gh", return_value=("", 0)):
            result = IntakeResult(sprint=71, passed=True)
            ms_num = check_milestone(71, result)
            assert ms_num is None
            assert find_code(result.findings, "MILESTONE_MISSING")


# --- Issue Tests ---

class TestIssues:
    def _mock_gh_issues(self, parent_num, parent_ms, task_issues):
        """Create issue data JSON for mocking."""
        data = [{
            "number": parent_num,
            "title": "[S71] Test Sprint",
            "milestone": {"title": parent_ms} if parent_ms else None,
            "state": "OPEN",
        }]
        for tid, inum, ms in task_issues:
            data.append({
                "number": inum,
                "title": f"[S71-{tid}] Task {tid}",
                "milestone": {"title": ms} if ms else None,
                "state": "OPEN",
            })
        return json.dumps(data)

    def test_all_issues_ok(self):
        data = self._mock_gh_issues(
            350, "Sprint 71",
            [("71.1", 351, "Sprint 71"), ("71.2", 352, "Sprint 71")]
        )
        with patch.object(intake, "gh", return_value=(data, 0)):
            plan = make_plan()
            result = IntakeResult(sprint=71, passed=True)
            check_issues(71, plan, result)
            assert find_code(result.findings, "PARENT_ISSUE_OK")
            assert not result.has_failures

    def test_parent_missing(self):
        with patch.object(intake, "gh", return_value=("", 1)):
            plan = make_plan()
            result = IntakeResult(sprint=71, passed=True)
            check_issues(71, plan, result)
            assert find_code(result.findings, "PARENT_ISSUE_MISSING")

    def test_parent_wrong_milestone(self):
        data = json.dumps([{
            "number": 350,
            "title": "[S71] Test Sprint",
            "milestone": {"title": "Sprint 70"},
            "state": "OPEN",
        }])
        with patch.object(intake, "gh", return_value=(data, 0)):
            plan = make_plan()
            result = IntakeResult(sprint=71, passed=True)
            check_issues(71, plan, result)
            assert find_code(result.findings, "PARENT_MILESTONE_WRONG")

    def test_task_issue_missing(self):
        # Only parent, no task issues — wider search also returns empty
        data = json.dumps([{
            "number": 350,
            "title": "[S71] Test Sprint",
            "milestone": {"title": "Sprint 71"},
            "state": "OPEN",
        }])
        with patch.object(intake, "gh", side_effect=[(data, 0), ("[]", 0), ("[]", 0)]):
            plan = make_plan()
            result = IntakeResult(sprint=71, passed=True)
            check_issues(71, plan, result)
            assert find_code(result.findings, "TASK_ISSUE_MISSING")

    def test_empty_json_response(self):
        with patch.object(intake, "gh", return_value=("[]", 0)):
            plan = make_plan()
            result = IntakeResult(sprint=71, passed=True)
            check_issues(71, plan, result)
            assert find_code(result.findings, "PARENT_ISSUE_MISSING")

    def test_invalid_json_response(self):
        with patch.object(intake, "gh", return_value=("not json", 0)):
            plan = make_plan()
            result = IntakeResult(sprint=71, passed=True)
            check_issues(71, plan, result)
            assert find_code(result.findings, "ISSUE_PARSE_ERROR")


# --- State Consistency Tests ---

class TestStateConsistency:
    @patch("subprocess.run")
    def test_state_consistent(self, mock_run):
        mock_run.return_value = MagicMock(returncode=0, stdout="PASS", stderr="")
        result = IntakeResult(sprint=71, passed=True)
        check_state_consistency(result)
        assert find_code(result.findings, "STATE_CONSISTENT")

    @patch("subprocess.run")
    def test_state_inconsistent(self, mock_run):
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="FAIL open-items stale",
            stderr=""
        )
        result = IntakeResult(sprint=71, passed=True)
        check_state_consistency(result)
        assert find_code(result.findings, "STATE_INCONSISTENT")
        assert find_severity(result.findings, "STATE_INCONSISTENT") == "FAIL"

    @patch("subprocess.run")
    def test_state_sync_timeout(self, mock_run):
        import subprocess as sp
        mock_run.side_effect = sp.TimeoutExpired(cmd="state-sync", timeout=30)
        result = IntakeResult(sprint=71, passed=True)
        check_state_consistency(result)
        assert find_code(result.findings, "STATE_SYNC_TIMEOUT")

    def test_state_sync_missing(self):
        with patch.object(intake, "REPO_ROOT", Path("/nonexistent")):
            result = IntakeResult(sprint=71, passed=True)
            check_state_consistency(result)
            assert find_code(result.findings, "STATE_SYNC_MISSING")


# --- Project Board Tests ---

class TestProjectBoard:
    def test_project_found_with_issues(self):
        responses = [
            ("PVT_test123", 0),
            (json.dumps([
                {"number": 350, "title": "[S71] Test"},
                {"number": 351, "title": "[S71-71.1] Task one"},
            ]), 0),
        ]
        with patch.object(intake, "gh", side_effect=responses):
            result = IntakeResult(sprint=71, passed=True)
            check_project_board(71, result)
            assert find_code(result.findings, "PROJECT_ISSUES_FOUND")

    def test_no_project_board(self):
        with patch.object(intake, "gh", return_value=("null", 0)):
            result = IntakeResult(sprint=71, passed=True)
            check_project_board(71, result)
            assert find_code(result.findings, "PROJECT_NOT_FOUND")
            assert find_severity(result.findings, "PROJECT_NOT_FOUND") == "WARN"

    def test_project_api_failure(self):
        with patch.object(intake, "gh", return_value=("", 1)):
            result = IntakeResult(sprint=71, passed=True)
            check_project_board(71, result)
            assert find_code(result.findings, "PROJECT_NOT_FOUND")

    def test_no_sprint_issues_on_board(self):
        with patch.object(intake, "gh", side_effect=[("PVT_test123", 0), ("[]", 0)]):
            result = IntakeResult(sprint=71, passed=True)
            check_project_board(71, result)
            assert find_code(result.findings, "PROJECT_NO_SPRINT_ISSUES")


# --- Load Plan Tests ---

class TestLoadPlan:
    def test_load_real_plan_71(self):
        """Integration test: load actual Sprint 71 plan.yaml."""
        plan, err = load_plan(71)
        if err and "not found" in err:
            pytest.skip("Sprint 71 plan.yaml not present")
        assert err is None
        assert plan is not None
        assert plan["sprint"] == 71

    def test_load_nonexistent_sprint(self):
        plan, err = load_plan(99999)
        assert plan is None
        assert "not found" in err


# --- Main Flow Integration Tests ---

class TestMainIntegration:
    def test_full_pass_flow(self):
        """Simulate a full intake check where everything passes."""
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan()
        check_plan_structure(plan, 71, result)
        assert find_code(result.findings, "PLAN_VALID")
        assert not result.has_failures

    def test_plan_load_error_flow(self):
        """Simulate plan load failure."""
        result = IntakeResult(sprint=99, passed=True)
        result.add("PLAN_LOAD_ERROR", "FAIL", "plan.yaml not found")
        result.passed = not result.has_failures
        assert not result.passed
        assert find_code(result.findings, "PLAN_LOAD_ERROR")

    def test_multiple_failures_accumulate(self):
        """Multiple checks can each add failures."""
        result = IntakeResult(sprint=71, passed=True)
        plan = make_plan(sprint=70, model="X", tasks=[])
        check_plan_structure(plan, 71, result)
        fail_count = sum(1 for f in result.findings if f.severity == "FAIL")
        assert fail_count >= 2  # sprint mismatch + invalid model + no tasks
