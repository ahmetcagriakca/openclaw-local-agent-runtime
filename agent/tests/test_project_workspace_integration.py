"""Integration tests for Project Workspace + Artifacts — D-145.

Task 74.11: End-to-end workspace and artifact lifecycle.
"""
import pytest

from persistence.mission_store import MissionStore
from persistence.project_store import (
    ProjectLifecycleError,
    ProjectStore,
)


@pytest.fixture
def full_setup(tmp_path):
    """Full integration setup: project + mission + workspace + artifact."""
    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(store_path=tmp_path / "projects.json",
                       mission_store=ms)
    return ps, ms, tmp_path


class TestWorkspaceLifecycle:
    """End-to-end workspace lifecycle."""

    def test_full_lifecycle(self, full_setup):
        """draft → active → enable workspace → publish → complete → archive."""
        ps, ms, tmp_path = full_setup

        # Create project
        proj = ps.create("Lifecycle Test", owner="akca")
        pid = proj["project_id"]
        assert proj["status"] == "draft"

        # Activate
        ps.transition_status(pid, "active")

        # Enable workspace
        result = ps.enable_workspace(pid,
                                      projects_root=tmp_path / "projects")
        assert result["workspace_root"] is not None

        # Create and link a mission
        artifact_file = tmp_path / "output" / "report.md"
        artifact_file.parent.mkdir(exist_ok=True)
        artifact_file.write_text("# Report\nResults here.")
        ms.record({
            "id": "mis_life", "goal": "lifecycle test",
            "status": "completed", "project_id": pid,
            "tokens": 500, "duration": 2.0, "stages": 2,
            "tools": 1, "reworks": 0, "ts": "2026-04-06T15:00:00Z",
            "artifacts": [
                {"id": "art_report", "path": str(artifact_file)}
            ],
            "stages_detail": [],
        })

        # Publish artifact
        entry = ps.publish_artifact(pid, "mis_life", "art_report")
        assert entry["published_to_project"] is True

        # List artifacts
        arts = ps.list_artifacts(pid)
        assert len(arts) == 1

        # Complete project
        ps.transition_status(pid, "completed")

        # Cannot unpublish after completion (immutable)
        with pytest.raises(ProjectLifecycleError):
            ps.unpublish_artifact(pid, "art_report")

        # Can still list artifacts
        arts = ps.list_artifacts(pid)
        assert len(arts) == 1

        # Archive
        ps.transition_status(pid, "archived")
        arts = ps.list_artifacts(pid)
        assert len(arts) == 1

    def test_workspace_enable_before_mission_link(self, full_setup):
        """Workspace can be enabled before any mission is linked."""
        ps, ms, tmp_path = full_setup
        proj = ps.create("Early WS")
        pid = proj["project_id"]
        ps.enable_workspace(pid, projects_root=tmp_path / "p")

        ws = ps.get_workspace(pid)
        assert ws["enabled"] is True
        assert ps.list_artifacts(pid) == []

    def test_multiple_artifacts_from_multiple_missions(self, full_setup):
        ps, ms, tmp_path = full_setup
        proj = ps.create("Multi")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")
        ps.enable_workspace(pid, projects_root=tmp_path / "p")

        for i in range(3):
            f = tmp_path / f"out{i}" / f"result{i}.json"
            f.parent.mkdir(exist_ok=True)
            f.write_text(f'{{"i": {i}}}')
            ms.record({
                "id": f"mis_{i}", "goal": f"test {i}",
                "status": "completed", "project_id": pid,
                "tokens": 100, "duration": 1.0, "stages": 1,
                "tools": 0, "reworks": 0,
                "ts": f"2026-04-06T{10+i}:00:00Z",
                "artifacts": [{"id": f"art_{i}", "path": str(f)}],
                "stages_detail": [],
            })
            ps.publish_artifact(pid, f"mis_{i}", f"art_{i}")

        all_arts = ps.list_artifacts(pid)
        assert len(all_arts) == 3

        # Filter by mission
        m1_arts = ps.list_artifacts(pid, mission_id="mis_1")
        assert len(m1_arts) == 1
        assert m1_arts[0]["mission_id"] == "mis_1"

    def test_unpublish_then_republish(self, full_setup):
        ps, ms, tmp_path = full_setup
        proj = ps.create("Repub")
        pid = proj["project_id"]
        ps.transition_status(pid, "active")
        ps.enable_workspace(pid, projects_root=tmp_path / "p")

        f = tmp_path / "o" / "data.csv"
        f.parent.mkdir(exist_ok=True)
        f.write_text("a,b\n1,2")
        ms.record({
            "id": "mis_r", "goal": "repub",
            "status": "completed", "project_id": pid,
            "tokens": 0, "duration": 0, "stages": 0,
            "tools": 0, "reworks": 0, "ts": "2026-04-06",
            "artifacts": [{"id": "art_r", "path": str(f)}],
            "stages_detail": [],
        })

        ps.publish_artifact(pid, "mis_r", "art_r")
        assert len(ps.list_artifacts(pid)) == 1

        ps.unpublish_artifact(pid, "art_r")
        assert len(ps.list_artifacts(pid)) == 0

        # Republish
        ps.publish_artifact(pid, "mis_r", "art_r")
        assert len(ps.list_artifacts(pid)) == 1


class TestEventTypes:
    """D-145: New event types registered correctly."""

    def test_new_event_types_in_catalog(self):
        from events.catalog import EventType
        assert hasattr(EventType, "PROJECT_WORKSPACE_ENABLED")
        assert hasattr(EventType, "PROJECT_ARTIFACT_PUBLISHED")
        assert hasattr(EventType, "PROJECT_ARTIFACT_UNPUBLISHED")
        assert EventType.PROJECT_WORKSPACE_ENABLED == "project.workspace_enabled"
        assert EventType.PROJECT_ARTIFACT_PUBLISHED == "project.artifact_published"
        assert EventType.PROJECT_ARTIFACT_UNPUBLISHED == "project.artifact_unpublished"

    def test_project_handler_accepts_new_events(self):
        from events.catalog import EventType
        from events.handlers.project_handler import PROJECT_EVENT_TYPES
        assert EventType.PROJECT_WORKSPACE_ENABLED in PROJECT_EVENT_TYPES
        assert EventType.PROJECT_ARTIFACT_PUBLISHED in PROJECT_EVENT_TYPES
        assert EventType.PROJECT_ARTIFACT_UNPUBLISHED in PROJECT_EVENT_TYPES

    def test_all_types_includes_new_events(self):
        from events.catalog import EventType
        all_types = EventType.all_types()
        assert "project.workspace_enabled" in all_types
        assert "project.artifact_published" in all_types
        assert "project.artifact_unpublished" in all_types
