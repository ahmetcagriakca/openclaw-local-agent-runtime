"""Tests for Historical Link model — D-144 §5.

Task 73.12: project_id retained, runtime influence stops, mission independence.
"""
import pytest

from persistence.mission_store import MissionStore
from persistence.project_store import (
    ProjectLifecycleError,
    ProjectStore,
)


@pytest.fixture
def stores(tmp_path):
    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(
        store_path=tmp_path / "projects.json",
        mission_store=ms,
    )
    return ps, ms


class TestHistoricalLink:
    """D-144 §5: When project goes inactive, mission retains project_id
    but operates independently."""

    def test_project_id_retained_after_completion(self, stores):
        ps, ms = stores
        proj = ps.create("Lifecycle Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        # Link a mission
        ms.record({"id": "mis-1", "goal": "test", "status": "completed",
                    "project_id": pid})

        # Complete the project
        ps.transition_status(pid, "completed")

        # Mission still has project_id
        mission = ms.get("mis-1")
        assert mission["project_id"] == pid

    def test_project_id_retained_after_cancellation(self, stores):
        ps, ms = stores
        proj = ps.create("Cancel Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-2", "goal": "test", "status": "failed",
                    "project_id": pid})

        ps.transition_status(pid, "cancelled")

        mission = ms.get("mis-2")
        assert mission["project_id"] == pid

    def test_project_id_retained_after_archive(self, stores):
        ps, ms = stores
        proj = ps.create("Archive Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-3", "goal": "test", "status": "completed",
                    "project_id": pid})

        ps.transition_status(pid, "completed")
        ps.transition_status(pid, "archived")

        mission = ms.get("mis-3")
        assert mission["project_id"] == pid

    def test_unlink_rejected_on_completed_project(self, stores):
        ps, ms = stores
        proj = ps.create("Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-4", "goal": "test", "status": "completed",
                    "project_id": pid})

        ps.transition_status(pid, "completed")

        with pytest.raises(ProjectLifecycleError, match="Historical"):
            ps.unlink_mission(pid, "mis-4")

    def test_unlink_rejected_on_archived_project(self, stores):
        ps, ms = stores
        proj = ps.create("Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "cancelled")
        ps.transition_status(pid, "archived")

        with pytest.raises(ProjectLifecycleError, match="Historical"):
            ps.unlink_mission(pid, "mis-5")

    def test_link_rejected_on_completed_project(self, stores):
        ps, ms = stores
        proj = ps.create("Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")
        ps.transition_status(pid, "completed")

        ms.record({"id": "mis-6", "goal": "test", "status": "pending"})

        with pytest.raises(ProjectLifecycleError):
            ps.link_mission(pid, "mis-6")

    def test_mission_operates_independently(self, stores):
        """Mission with historical link can still be recorded/updated."""
        ps, ms = stores
        proj = ps.create("Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-7", "goal": "test", "status": "running",
                    "project_id": pid})

        # Complete the missions first (so project can complete)
        ms.record({"id": "mis-7", "goal": "test", "status": "completed",
                    "project_id": pid})

        ps.transition_status(pid, "completed")

        # Mission can still be updated independently
        mission = ms.get("mis-7")
        assert mission["status"] == "completed"
        assert mission["project_id"] == pid

    def test_multiple_missions_retain_links(self, stores):
        ps, ms = stores
        proj = ps.create("Multi Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        for i in range(3):
            ms.record({"id": f"mis-{i}", "goal": f"task {i}",
                        "status": "completed", "project_id": pid})

        ps.transition_status(pid, "completed")

        for i in range(3):
            m = ms.get(f"mis-{i}")
            assert m["project_id"] == pid


class TestDeleteHistoricalLink:
    """D-144 §5: Soft-delete preserves historical links."""

    def test_delete_preserves_mission_project_id(self, stores):
        ps, ms = stores
        proj = ps.create("Delete Link Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-d1", "goal": "test", "status": "completed",
                    "project_id": pid})

        # Soft-delete (cancel) the project
        ps.transition_status(pid, "cancelled")

        # Mission retains project_id
        mission = ms.get("mis-d1")
        assert mission["project_id"] == pid
