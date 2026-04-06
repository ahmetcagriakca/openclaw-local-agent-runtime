"""Tests for pre-implementation-check.py — Session entry gate validation.

T72.3: Unit tests for the session entry gate tool.
Tests cover file existence checks, blocker detection, state-sync delegation,
previous sprint closure detection, plan.yaml detection, and JSON output.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock
from subprocess import CompletedProcess

import pytest

# Add tools/ to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "tools"))

from importlib import import_module

pic = import_module("pre-implementation-check")

CheckResult = pic.CheckResult
GateResult = pic.GateResult
check_file_exists = pic.check_file_exists
check_active_blockers = pic.check_active_blockers
check_previous_sprint_closed = pic.check_previous_sprint_closed
check_plan_yaml = pic.check_plan_yaml
check_state_sync = pic.check_state_sync
detect_active_sprint = pic.detect_active_sprint
extract_last_closed_sprint = pic.extract_last_closed_sprint
extract_next_sprint = pic.extract_next_sprint
run_gate = pic.run_gate
astuple = pic.astuple


# ── CheckResult Tests ────────────────────────────────────────────────


class TestCheckResult:
    def test_create_passed(self):
        cr = CheckResult("TEST", True, "ok")
        assert cr.passed is True
        assert cr.name == "TEST"

    def test_create_failed(self):
        cr = CheckResult("TEST", False, "bad")
        assert cr.passed is False


# ── GateResult Tests ─────────────────────────────────────────────────


class TestGateResult:
    def test_empty_gate_passes(self):
        g = GateResult()
        assert g.passed is True
        assert g.fail_count == 0

    def test_all_pass(self):
        g = GateResult()
        g.add("A", True, "ok")
        g.add("B", True, "ok")
        assert g.passed is True
        assert g.fail_count == 0

    def test_one_fail(self):
        g = GateResult()
        g.add("A", True, "ok")
        g.add("B", False, "bad")
        assert g.passed is False
        assert g.fail_count == 1

    def test_multiple_fails(self):
        g = GateResult()
        g.add("A", False, "bad1")
        g.add("B", False, "bad2")
        g.add("C", True, "ok")
        assert g.fail_count == 2


# ── check_file_exists Tests ─────────────────────────────────────────


class TestCheckFileExists:
    def test_existing_file(self, tmp_path):
        f = tmp_path / "test.md"
        f.write_text("content", encoding="utf-8")
        with patch.object(pic, "REPO_ROOT", tmp_path):
            result = check_file_exists(f, "TEST_FILE")
        assert result.passed is True
        assert "exists" in result.message

    def test_missing_file(self, tmp_path):
        f = tmp_path / "missing.md"
        with patch.object(pic, "REPO_ROOT", tmp_path):
            result = check_file_exists(f, "TEST_FILE")
        assert result.passed is False
        assert "not found" in result.message

    def test_empty_file(self, tmp_path):
        f = tmp_path / "empty.md"
        f.write_text("", encoding="utf-8")
        with patch.object(pic, "REPO_ROOT", tmp_path):
            result = check_file_exists(f, "TEST_FILE")
        assert result.passed is False
        assert "empty" in result.message


# ── extract_last_closed_sprint Tests ─────────────────────────────────


class TestExtractLastClosedSprint:
    def test_standard_format(self):
        content = "Sprint 71 closed. Phase 9 active."
        assert extract_last_closed_sprint(content) == 71

    def test_table_format(self):
        content = "| Sprint 70 | Validator Hardening | Closed |"
        assert extract_last_closed_sprint(content) == 70

    def test_no_match(self):
        content = "No sprint info here."
        assert extract_last_closed_sprint(content) is None


# ── extract_next_sprint Tests ────────────────────────────────────────


class TestExtractNextSprint:
    def test_not_started_in_table(self):
        content = "| S72 | Session Protocol | Not started |"
        assert extract_next_sprint(content) == 72

    def test_no_match(self):
        content = "All sprints closed."
        assert extract_next_sprint(content) is None


# ── detect_active_sprint Tests ───────────────────────────────────────


class TestDetectActiveSprint:
    def test_from_state_md(self, tmp_path):
        state_dir = tmp_path / "docs" / "ai"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "STATE.md"
        state_file.write_text(
            "| S72 | Session Protocol | Not started |\n",
            encoding="utf-8",
        )
        with patch.object(pic, "REPO_ROOT", tmp_path):
            assert detect_active_sprint() == 72

    def test_fallback_last_closed_plus_one(self, tmp_path):
        state_dir = tmp_path / "docs" / "ai"
        state_dir.mkdir(parents=True)
        state_file = state_dir / "STATE.md"
        state_file.write_text("Sprint 71 closed.", encoding="utf-8")
        with patch.object(pic, "REPO_ROOT", tmp_path):
            assert detect_active_sprint() == 72

    def test_no_state_file(self, tmp_path):
        with patch.object(pic, "REPO_ROOT", tmp_path):
            assert detect_active_sprint() is None


# ── check_active_blockers Tests ──────────────────────────────────────


class TestCheckActiveBlockers:
    def test_no_blockers(self, tmp_path):
        f = tmp_path / "open-items.md"
        f.write_text(
            "## Active Blockers\n\n| # | Item |\n|---|------|\n| — | *(none)* |\n",
            encoding="utf-8",
        )
        result = check_active_blockers(f, allow_blockers=False)
        assert result.passed is True

    def test_has_blockers(self, tmp_path):
        f = tmp_path / "open-items.md"
        f.write_text(
            "## Active Blockers\n\n| # | Item |\n|---|------|\n| 1 | Something broken |\n",
            encoding="utf-8",
        )
        result = check_active_blockers(f, allow_blockers=False)
        assert result.passed is False

    def test_blockers_allowed(self, tmp_path):
        f = tmp_path / "open-items.md"
        f.write_text(
            "## Active Blockers\n\n| # | Item |\n|---|------|\n| 1 | Something broken |\n",
            encoding="utf-8",
        )
        result = check_active_blockers(f, allow_blockers=True)
        assert result.passed is True
        assert "--allow-blockers" in result.message

    def test_missing_file(self, tmp_path):
        f = tmp_path / "missing.md"
        result = check_active_blockers(f, allow_blockers=False)
        assert result.passed is False

    def test_no_blocker_section(self, tmp_path):
        f = tmp_path / "open-items.md"
        f.write_text("# Open Items\nSome content.\n", encoding="utf-8")
        result = check_active_blockers(f, allow_blockers=False)
        assert result.passed is True


# ── check_previous_sprint_closed Tests ───────────────────────────────


class TestCheckPreviousSprintClosed:
    def test_sprint_closed(self, tmp_path):
        f = tmp_path / "current.md"
        f.write_text("S71 closed. Phase 9 active.", encoding="utf-8")
        result = check_previous_sprint_closed(f)
        assert result.passed is True
        assert "71" in result.message

    def test_last_closed_sprint_format(self, tmp_path):
        f = tmp_path / "current.md"
        f.write_text("Last closed sprint: 71\n", encoding="utf-8")
        result = check_previous_sprint_closed(f)
        assert result.passed is True

    def test_no_closure_info(self, tmp_path):
        f = tmp_path / "current.md"
        f.write_text("Sprint 72 in progress.", encoding="utf-8")
        result = check_previous_sprint_closed(f)
        assert result.passed is False

    def test_missing_handoff(self, tmp_path):
        f = tmp_path / "missing.md"
        result = check_previous_sprint_closed(f)
        assert result.passed is False


# ── check_plan_yaml Tests ────────────────────────────────────────────


class TestCheckPlanYaml:
    def test_plan_exists(self, tmp_path):
        plan_dir = tmp_path / "docs" / "sprints" / "sprint-72"
        plan_dir.mkdir(parents=True)
        (plan_dir / "plan.yaml").write_text("sprint: 72\n", encoding="utf-8")
        with patch.object(pic, "REPO_ROOT", tmp_path):
            result = check_plan_yaml(72)
        assert result.passed is True

    def test_plan_missing(self, tmp_path):
        with patch.object(pic, "REPO_ROOT", tmp_path):
            result = check_plan_yaml(72)
        assert result.passed is False

    def test_none_sprint(self):
        result = check_plan_yaml(None)
        assert result.passed is False
        assert "Could not detect" in result.message


# ── check_state_sync Tests ───────────────────────────────────────────


class TestCheckStateSync:
    def test_pass(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(args=[], returncode=0, stdout="PASS", stderr="")
            result = check_state_sync()
        assert result.passed is True

    def test_fail(self):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = CompletedProcess(
                args=[], returncode=1, stdout="", stderr="FAIL open-items stale"
            )
            result = check_state_sync()
        assert result.passed is False

    def test_timeout(self):
        from subprocess import TimeoutExpired
        with patch("subprocess.run", side_effect=TimeoutExpired("cmd", 30)):
            result = check_state_sync()
        assert result.passed is False
        assert "timed out" in result.message

    def test_missing_script(self):
        with patch("subprocess.run", side_effect=FileNotFoundError):
            result = check_state_sync()
        assert result.passed is False
        assert "not found" in result.message


# ── astuple Tests ────────────────────────────────────────────────────


class TestAstuple:
    def test_converts_to_tuple(self):
        cr = CheckResult("NAME", True, "msg")
        t = astuple(cr)
        assert t == ("NAME", True, "msg")


# ── run_gate Integration Tests ───────────────────────────────────────


class TestRunGate:
    def test_full_pass(self, tmp_path):
        """Test run_gate with all files present and state-sync passing."""
        # Set up directory structure
        handoff_dir = tmp_path / "docs" / "ai" / "handoffs"
        handoff_dir.mkdir(parents=True)
        state_dir = tmp_path / "docs" / "ai" / "state"
        state_dir.mkdir(parents=True)
        ai_dir = tmp_path / "docs" / "ai"
        sprint_dir = tmp_path / "docs" / "sprints" / "sprint-72"
        sprint_dir.mkdir(parents=True)

        (handoff_dir / "current.md").write_text("S71 closed. Phase 9.", encoding="utf-8")
        (state_dir / "open-items.md").write_text(
            "## Active Blockers\n| # | Item |\n|---|---|\n| — | *(none)* |\n",
            encoding="utf-8",
        )
        (ai_dir / "STATE.md").write_text(
            "| S72 | Session Protocol | Not started |\n",
            encoding="utf-8",
        )
        (sprint_dir / "plan.yaml").write_text("sprint: 72\n", encoding="utf-8")

        with patch.object(pic, "REPO_ROOT", tmp_path), \
             patch.object(pic, "check_state_sync", return_value=CheckResult("STATE_SYNC_PASS", True, "PASS")):
            gate = run_gate()

        assert gate.passed is True
        assert gate.verdict == "PASS"
        assert gate.fail_count == 0

    def test_missing_handoff_fails(self, tmp_path):
        """Test that missing handoff causes FAIL."""
        state_dir = tmp_path / "docs" / "ai" / "state"
        state_dir.mkdir(parents=True)
        ai_dir = tmp_path / "docs" / "ai"
        (state_dir / "open-items.md").write_text("## Active Blockers\n| — | *(none)* |\n", encoding="utf-8")
        (ai_dir / "STATE.md").write_text("Sprint 71 closed.", encoding="utf-8")

        with patch.object(pic, "REPO_ROOT", tmp_path), \
             patch.object(pic, "check_state_sync", return_value=CheckResult("STATE_SYNC_PASS", True, "PASS")):
            gate = run_gate()

        assert gate.passed is False
        assert gate.fail_count >= 1
        failed_names = [c.name for c in gate.checks if not c.passed]
        assert "HANDOFF_EXISTS" in failed_names

    def test_allow_blockers_flag(self, tmp_path):
        """Test --allow-blockers passes even with active blockers."""
        handoff_dir = tmp_path / "docs" / "ai" / "handoffs"
        handoff_dir.mkdir(parents=True)
        state_dir = tmp_path / "docs" / "ai" / "state"
        state_dir.mkdir(parents=True)
        ai_dir = tmp_path / "docs" / "ai"
        sprint_dir = tmp_path / "docs" / "sprints" / "sprint-72"
        sprint_dir.mkdir(parents=True)

        (handoff_dir / "current.md").write_text("S71 closed.", encoding="utf-8")
        (state_dir / "open-items.md").write_text(
            "## Active Blockers\n| # | Item |\n|---|---|\n| 1 | Bug |\n",
            encoding="utf-8",
        )
        (ai_dir / "STATE.md").write_text("| S72 | Protocol | Not started |", encoding="utf-8")
        (sprint_dir / "plan.yaml").write_text("sprint: 72\n", encoding="utf-8")

        with patch.object(pic, "REPO_ROOT", tmp_path), \
             patch.object(pic, "check_state_sync", return_value=CheckResult("STATE_SYNC_PASS", True, "PASS")):
            gate = run_gate(allow_blockers=True)

        assert gate.passed is True
