"""Integration test: full CRUD + link lifecycle — D-144.

Task 73.14: End-to-end project lifecycle with missions.
"""
import pytest

from persistence.mission_store import MissionStore
from persistence.project_store import (
    ActiveMissionsError,
    ProjectLifecycleError,
    ProjectStore,
)


@pytest.fixture
def env(tmp_path):
    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(
        store_path=tmp_path / "projects.json",
        mission_store=ms,
    )
    return ps, ms


class TestFullProjectLifecycle:
    """Complete lifecycle: create → activate → link → complete → archive."""

    def test_happy_path(self, env):
        ps, ms = env

        # 1. Create project
        proj = ps.create("Feature X", description="Multi-mission feature")
        pid = proj["project_id"]
        assert proj["status"] == "draft"

        # 2. Activate
        proj = ps.transition_status(pid, "active")
        assert proj["status"] == "active"

        # 3. Link missions
        ms.record({"id": "mis-1", "goal": "backend", "status": "pending"})
        ms.record({"id": "mis-2", "goal": "frontend", "status": "pending"})
        ps.link_mission(pid, "mis-1")
        ps.link_mission(pid, "mis-2")

        assert ms.get("mis-1")["project_id"] == pid
        assert ms.get("mis-2")["project_id"] == pid

        # 4. Mission summary reflects links
        summary = ps.get_mission_summary(pid)
        assert summary["total"] == 2
        assert summary["active_count"] == 2

        # 5. Cannot complete with active missions
        with pytest.raises(ActiveMissionsError):
            ps.transition_status(pid, "completed")

        # 6. Missions complete
        ms.record({"id": "mis-1", "goal": "backend", "status": "completed",
                    "project_id": pid})
        ms.record({"id": "mis-2", "goal": "frontend", "status": "completed",
                    "project_id": pid})

        # 7. Now complete succeeds
        proj = ps.transition_status(pid, "completed")
        assert proj["status"] == "completed"

        summary = ps.get_mission_summary(pid)
        assert summary["quiescent_count"] == 2
        assert summary["active_count"] == 0

        # 8. Archive
        proj = ps.transition_status(pid, "archived")
        assert proj["status"] == "archived"

        # 9. Historical links preserved
        assert ms.get("mis-1")["project_id"] == pid
        assert ms.get("mis-2")["project_id"] == pid

        # 10. Cannot link/unlink on archived
        with pytest.raises(ProjectLifecycleError):
            ps.link_mission(pid, "mis-3")
        with pytest.raises(ProjectLifecycleError):
            ps.unlink_mission(pid, "mis-1")

    def test_cancel_path(self, env):
        """draft → active → cancel → archive"""
        ps, ms = env

        proj = ps.create("Abandoned Work")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-c1", "goal": "test", "status": "failed",
                    "project_id": pid})

        proj = ps.transition_status(pid, "cancelled")
        assert proj["status"] == "cancelled"

        proj = ps.transition_status(pid, "archived")
        assert proj["status"] == "archived"

    def test_pause_resume_path(self, env):
        """draft → active → paused → active → completed → archived"""
        ps, ms = env

        proj = ps.create("Paused Work")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")
        ps.transition_status(pid, "paused")

        # Cannot link during pause
        ms.record({"id": "mis-p1", "goal": "test", "status": "pending"})
        with pytest.raises(ProjectLifecycleError):
            ps.link_mission(pid, "mis-p1")

        # Resume
        ps.transition_status(pid, "active")

        # Now can link
        ps.link_mission(pid, "mis-p1")
        assert ms.get("mis-p1")["project_id"] == pid

        # Complete mission then project
        ms.record({"id": "mis-p1", "goal": "test", "status": "completed",
                    "project_id": pid})
        ps.transition_status(pid, "completed")
        ps.transition_status(pid, "archived")

    def test_unlink_and_relink(self, env):
        ps, ms = env

        proj = ps.create("Relink Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-r1", "goal": "test", "status": "pending"})
        ps.link_mission(pid, "mis-r1")
        assert ms.get("mis-r1")["project_id"] == pid

        ps.unlink_mission(pid, "mis-r1")
        assert ms.get("mis-r1")["project_id"] is None

        ps.link_mission(pid, "mis-r1")
        assert ms.get("mis-r1")["project_id"] == pid

    def test_delete_draft_project(self, env):
        ps, ms = env

        proj = ps.create("Draft Delete")
        pid = proj["project_id"]

        result = ps.delete(pid)
        assert result["status"] == "cancelled"
        assert "deleted_at" in result

    def test_delete_active_with_quiescent_missions(self, env):
        ps, ms = env

        proj = ps.create("Active Delete")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        ms.record({"id": "mis-d1", "goal": "test", "status": "completed",
                    "project_id": pid})

        result = ps.delete(pid)
        assert result["status"] == "cancelled"

    def test_multiple_projects_independent(self, env):
        ps, ms = env

        proj1 = ps.create("Project A")
        proj2 = ps.create("Project B")
        ps.transition_status(proj1["project_id"], "active")
        ps.transition_status(proj2["project_id"], "active")

        ms.record({"id": "mis-a1", "goal": "for A", "status": "running"})
        ms.record({"id": "mis-b1", "goal": "for B", "status": "completed"})
        ps.link_mission(proj1["project_id"], "mis-a1")
        ps.link_mission(proj2["project_id"], "mis-b1")

        # Project B can complete (all quiescent), A cannot
        ps.transition_status(proj2["project_id"], "completed")
        with pytest.raises(ActiveMissionsError):
            ps.transition_status(proj1["project_id"], "completed")

    def test_project_persistence_roundtrip(self, env):
        ps, ms = env

        proj = ps.create("Persist Test")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")

        # Reload
        ps2 = ProjectStore(
            store_path=ps._path,
            mission_store=ms,
        )
        loaded = ps2.get(pid)
        assert loaded is not None
        assert loaded["status"] == "active"
        assert loaded["name"] == "Persist Test"
