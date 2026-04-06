"""Tests for tools/state-sync.py --check mode (D-142 governed doc consistency)."""

import importlib.util
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest

REPO_ROOT = Path(__file__).parent.parent

# Import hyphenated script module via importlib
_spec = importlib.util.spec_from_file_location("state_sync", REPO_ROOT / "tools" / "state-sync.py")
state_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(state_sync)


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def governed_dir(tmp_path):
    """Create a governed doc set in tmp_path with consistent state."""
    # Create directory structure
    (tmp_path / "docs" / "ai" / "handoffs").mkdir(parents=True)
    (tmp_path / "docs" / "ai" / "state").mkdir(parents=True)
    (tmp_path / "docs" / "ai").mkdir(parents=True, exist_ok=True)
    (tmp_path / "docs" / "decisions").mkdir(parents=True)

    # Handoff — current.md
    (tmp_path / "docs" / "ai" / "handoffs" / "current.md").write_text(textwrap.dedent("""\
        # Session Handoff
        ## Current State
        - **Phase:** 9 active — S69 in progress
        - **Last closed sprint:** 68
        - **Decisions:** 139 frozen + 2 superseded
    """), encoding="utf-8")

    # open-items.md
    (tmp_path / "docs" / "ai" / "state" / "open-items.md").write_text(textwrap.dedent("""\
        # open-items.md
        ## Next Sprint
        **Phase 9 active.** S69 ready.
    """), encoding="utf-8")

    # STATE.md
    (tmp_path / "docs" / "ai" / "STATE.md").write_text(textwrap.dedent("""\
        # Current State
        **Active phase:** Phase 9 — Sprint 69 active
        **Note:** 139 frozen decisions + 2 superseded (D-001 → D-142).
    """), encoding="utf-8")

    # NEXT.md
    (tmp_path / "docs" / "ai" / "NEXT.md").write_text(textwrap.dedent("""\
        # Next Steps
        **Current:** Phase 9 active. Sprint 68 closed. S69 next.
    """), encoding="utf-8")

    # DECISIONS.md (with index line matching)
    (tmp_path / "docs" / "ai" / "DECISIONS.md").write_text(textwrap.dedent("""\
        # Decisions
        ## Decision Index
        139 frozen + 2 superseded decisions.
    """), encoding="utf-8")

    return tmp_path


def _patch_paths(governed_dir):
    """Return a dict of patches mapping module-level paths to governed_dir."""
    return {
        "HANDOFF_FILE": governed_dir / "docs" / "ai" / "handoffs" / "current.md",
        "OPEN_ITEMS_FILE": governed_dir / "docs" / "ai" / "state" / "open-items.md",
        "STATE_FILE": governed_dir / "docs" / "ai" / "STATE.md",
        "NEXT_FILE": governed_dir / "docs" / "ai" / "NEXT.md",
        "DECISIONS_FILE": governed_dir / "docs" / "ai" / "DECISIONS.md",
        "REPO_ROOT": governed_dir,
        "GOVERNED_FILES": [
            governed_dir / "docs" / "ai" / "handoffs" / "current.md",
            governed_dir / "docs" / "ai" / "state" / "open-items.md",
            governed_dir / "docs" / "ai" / "STATE.md",
            governed_dir / "docs" / "ai" / "NEXT.md",
        ],
    }


# ── Tests ────────────────────────────────────────────────────────────────────


class TestAlignedState:
    """All governed docs consistent → PASS."""

    def test_aligned_state_passes(self, governed_dir, capsys):
        patches = _patch_paths(governed_dir)
        with patch.multiple(state_sync, **patches):
            result = state_sync.run_governed_check()
        assert result == 0
        captured = capsys.readouterr()
        assert "PASS" in captured.out


class TestSprintMismatch:
    """Sprint number mismatch between handoff and STATE.md → FAIL."""

    def test_sprint_mismatch_fails(self, governed_dir, capsys):
        # Make STATE.md say sprint 67 closed instead of 68
        (governed_dir / "docs" / "ai" / "STATE.md").write_text(textwrap.dedent("""\
            # Current State
            **Active phase:** Phase 9 active
            **Note:** Last closed sprint: 67. 139 frozen decisions + 2 superseded.
        """), encoding="utf-8")
        # Handoff still says last closed sprint: 68
        patches = _patch_paths(governed_dir)
        with patch.multiple(state_sync, **patches):
            result = state_sync.run_governed_check()
        assert result == 1
        captured = capsys.readouterr()
        assert "SPRINT MISMATCH" in captured.out or "FAIL" in captured.out


class TestPhaseMismatch:
    """NEXT.md phase mismatch → FAIL."""

    def test_next_md_phase_mismatch_fails(self, governed_dir, capsys):
        # STATE.md says Phase 9 (from fixture), NEXT.md says Phase 8
        (governed_dir / "docs" / "ai" / "NEXT.md").write_text(textwrap.dedent("""\
            # Next Steps
            **Current:** Phase 8 active. S68 closed.
        """), encoding="utf-8")
        # Also ensure STATE.md explicitly has Phase 9 extractable
        (governed_dir / "docs" / "ai" / "STATE.md").write_text(textwrap.dedent("""\
            # Current State
            **Active phase:** Phase 9 active
            **Note:** 139 frozen decisions + 2 superseded.
        """), encoding="utf-8")
        patches = _patch_paths(governed_dir)
        with patch.multiple(state_sync, **patches):
            result = state_sync.run_governed_check()
        assert result == 1
        captured = capsys.readouterr()
        assert "NEXT.md phase" in captured.out or "PHASE MISMATCH" in captured.out


class TestStaleOpenItems:
    """open-items.md next sprint <= last closed → FAIL."""

    def test_stale_open_items_fails(self, governed_dir, capsys):
        # open-items says S65 ready but last closed is 68
        (governed_dir / "docs" / "ai" / "state" / "open-items.md").write_text(textwrap.dedent("""\
            # open-items.md
            ## Next Sprint
            **Phase 9 active.** S65 ready.
        """), encoding="utf-8")
        # Ensure STATE.md has extractable last closed sprint
        (governed_dir / "docs" / "ai" / "STATE.md").write_text(textwrap.dedent("""\
            # Current State
            **Active phase:** Phase 9 active
            **Note:** S68 closed. 139 frozen decisions + 2 superseded.
        """), encoding="utf-8")
        patches = _patch_paths(governed_dir)
        with patch.multiple(state_sync, **patches):
            result = state_sync.run_governed_check()
        assert result == 1
        captured = capsys.readouterr()
        assert "stale" in captured.out.lower() or "FAIL" in captured.out


class TestMissingGoverned:
    """Missing governed file → FAIL."""

    def test_missing_file_fails(self, governed_dir, capsys):
        # Delete one governed file
        (governed_dir / "docs" / "ai" / "NEXT.md").unlink()
        patches = _patch_paths(governed_dir)
        with patch.multiple(state_sync, **patches):
            result = state_sync.run_governed_check()
        assert result == 1
        captured = capsys.readouterr()
        assert "MISSING" in captured.out


class TestDecisionCountMismatch:
    """DECISIONS.md count != STATE.md count → FAIL."""

    def test_decision_count_mismatch_fails(self, governed_dir, capsys):
        # STATE.md says 135 frozen but DECISIONS.md says 139
        (governed_dir / "docs" / "ai" / "STATE.md").write_text(textwrap.dedent("""\
            # Current State
            **Active phase:** Phase 9 — Sprint 69 active
            **Note:** 135 frozen decisions + 2 superseded.
        """), encoding="utf-8")
        patches = _patch_paths(governed_dir)
        with patch.multiple(state_sync, **patches):
            result = state_sync.run_governed_check()
        assert result == 1
        captured = capsys.readouterr()
        assert "DECISION COUNT MISMATCH" in captured.out


class TestExtractors:
    """Unit tests for field extraction functions."""

    def test_extract_last_closed_sprint(self):
        assert state_sync.extract_last_closed_sprint("Last closed sprint: 68") == 68
        assert state_sync.extract_last_closed_sprint("S68 closed") == 68
        assert state_sync.extract_last_closed_sprint("Sprint 68 closed") == 68
        assert state_sync.extract_last_closed_sprint("nothing here") is None

    def test_extract_current_phase(self):
        assert state_sync.extract_current_phase("Phase 9 active") == 9
        assert state_sync.extract_current_phase("**Active phase:** Phase 9") == 9
        assert state_sync.extract_current_phase("nothing here") is None

    def test_extract_next_sprint(self):
        assert state_sync.extract_next_sprint("S69 ready") == 69
        assert state_sync.extract_next_sprint("nothing") is None

    def test_extract_decision_counts(self):
        frozen, sup = state_sync.extract_decision_counts_from_file(
            "139 frozen decisions + 2 superseded"
        )
        assert frozen == 139
        assert sup == 2

        frozen2, sup2 = state_sync.extract_decision_counts_from_file("no info")
        assert frozen2 is None
