"""Tests for Project Status FSM — D-144 §4.

Task 73.11: Valid/invalid transitions, quiescent checks, FSM exhaustive.
"""

import pytest

from persistence.mission_store import MissionStore
from persistence.project_store import (
    VALID_PROJECT_TRANSITIONS,
    ActiveMissionsError,
    InvalidTransitionError,
    ProjectStatus,
    ProjectStore,
)


@pytest.fixture
def store(tmp_path):
    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(
        store_path=tmp_path / "projects.json",
        mission_store=ms,
    )
    return ps, ms


class TestValidTransitions:
    """D-144 §4: All valid transitions succeed."""

    def test_draft_to_active(self, store):
        ps, _ = store
        proj = ps.create("Test")
        result = ps.transition_status(proj["project_id"], "active")
        assert result["status"] == "active"

    def test_draft_to_cancelled(self, store):
        ps, _ = store
        proj = ps.create("Test")
        result = ps.transition_status(proj["project_id"], "cancelled")
        assert result["status"] == "cancelled"

    def test_active_to_paused(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        result = ps.transition_status(proj["project_id"], "paused")
        assert result["status"] == "paused"

    def test_active_to_completed_no_missions(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        result = ps.transition_status(proj["project_id"], "completed")
        assert result["status"] == "completed"

    def test_active_to_cancelled_no_missions(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        result = ps.transition_status(proj["project_id"], "cancelled")
        assert result["status"] == "cancelled"

    def test_paused_to_active(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ps.transition_status(proj["project_id"], "paused")
        result = ps.transition_status(proj["project_id"], "active")
        assert result["status"] == "active"

    def test_paused_to_cancelled(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ps.transition_status(proj["project_id"], "paused")
        result = ps.transition_status(proj["project_id"], "cancelled")
        assert result["status"] == "cancelled"

    def test_completed_to_archived(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        ps.transition_status(proj["project_id"], "completed")
        result = ps.transition_status(proj["project_id"], "archived")
        assert result["status"] == "archived"

    def test_cancelled_to_archived(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "cancelled")
        result = ps.transition_status(proj["project_id"], "archived")
        assert result["status"] == "archived"


class TestInvalidTransitions:
    """D-144 §4: Invalid transitions rejected with InvalidTransitionError."""

    def test_draft_to_paused(self, store):
        ps, _ = store
        proj = ps.create("Test")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "paused")

    def test_draft_to_completed(self, store):
        ps, _ = store
        proj = ps.create("Test")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "completed")

    def test_draft_to_archived(self, store):
        ps, _ = store
        proj = ps.create("Test")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "archived")

    def test_active_to_draft(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "draft")

    def test_active_to_archived(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "archived")

    def test_archived_to_anything(self, store):
        ps, _ = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "cancelled")
        ps.transition_status(proj["project_id"], "archived")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "active")

    def test_invalid_status_string(self, store):
        ps, _ = store
        proj = ps.create("Test")
        with pytest.raises(InvalidTransitionError):
            ps.transition_status(proj["project_id"], "nonexistent")

    def test_nonexistent_project(self, store):
        ps, _ = store
        with pytest.raises(Exception, match="not found"):
            ps.transition_status("proj_fake", "active")


class TestQuiescentCheck:
    """D-144 §4: Complete/cancel blocked by active missions."""

    def test_complete_blocked_by_running_mission(self, store):
        ps, ms = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")

        # Add a running mission linked to project
        ms.record({
            "id": "mis-1",
            "goal": "test",
            "status": "running",
            "project_id": proj["project_id"],
        })

        with pytest.raises(ActiveMissionsError) as exc_info:
            ps.transition_status(proj["project_id"], "completed")
        assert "mis-1" in exc_info.value.mission_ids

    def test_cancel_blocked_by_pending_mission(self, store):
        ps, ms = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")

        ms.record({
            "id": "mis-2",
            "goal": "test",
            "status": "pending",
            "project_id": proj["project_id"],
        })

        with pytest.raises(ActiveMissionsError):
            ps.transition_status(proj["project_id"], "cancelled")

    def test_complete_allowed_with_quiescent_missions(self, store):
        ps, ms = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")

        ms.record({
            "id": "mis-3",
            "goal": "test",
            "status": "completed",
            "project_id": proj["project_id"],
        })
        ms.record({
            "id": "mis-4",
            "goal": "test",
            "status": "failed",
            "project_id": proj["project_id"],
        })

        result = ps.transition_status(proj["project_id"], "completed")
        assert result["status"] == "completed"

    def test_complete_allowed_with_timed_out_mission(self, store):
        ps, ms = store
        proj = ps.create("Test")
        ps.transition_status(proj["project_id"], "active")

        ms.record({
            "id": "mis-5",
            "goal": "test",
            "status": "timed_out",
            "project_id": proj["project_id"],
        })

        result = ps.transition_status(proj["project_id"], "completed")
        assert result["status"] == "completed"


class TestTransitionMatrixExhaustive:
    """Verify VALID_PROJECT_TRANSITIONS covers all 6 states."""

    def test_all_states_in_matrix(self):
        for status in ProjectStatus:
            assert status in VALID_PROJECT_TRANSITIONS, (
                f"{status} missing from transition matrix")

    def test_archived_is_terminal(self):
        assert VALID_PROJECT_TRANSITIONS[ProjectStatus.ARCHIVED] == set()
