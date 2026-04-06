"""Tests for Artifact Publish/Unpublish — D-145 §3.

Task 74.10: Publish, list, unpublish artifacts.
"""
import pytest

from persistence.mission_store import MissionStore
from persistence.project_store import (
    ProjectLifecycleError,
    ProjectStore,
    ProjectStoreError,
)


@pytest.fixture
def setup(tmp_path):
    """Full setup with project store, mission store, and artifact file."""
    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(
        store_path=tmp_path / "projects.json",
        mission_store=ms,
    )
    # Create project with workspace
    proj = ps.create("Artifact Test")
    pid = proj["project_id"]
    ps.transition_status(pid, "active")
    ps.enable_workspace(pid, projects_root=tmp_path / "projects")

    # Create mission linked to project
    mission = {
        "id": "mis_001",
        "goal": "test mission",
        "status": "completed",
        "project_id": pid,
        "tokens": 100,
        "duration": 1.0,
        "stages": 1,
        "tools": 0,
        "reworks": 0,
        "ts": "2026-04-06T12:00:00Z",
        "artifacts": [
            {
                "id": "art_001",
                "path": str(tmp_path / "mission_output" / "result.json"),
                "type": "stage_output",
            }
        ],
        "stages_detail": [],
    }
    ms.record(mission)

    # Create the actual artifact file
    artifact_dir = tmp_path / "mission_output"
    artifact_dir.mkdir(exist_ok=True)
    artifact_file = artifact_dir / "result.json"
    artifact_file.write_text('{"result": "ok"}')

    return ps, ms, pid, tmp_path


class TestPublishArtifact:
    def test_publish_copies_file(self, setup):
        ps, ms, pid, tmp_path = setup
        entry = ps.publish_artifact(pid, "mis_001", "art_001")
        assert entry["artifact_id"] == "art_001"
        assert entry["mission_id"] == "mis_001"
        assert entry["published_to_project"] is True
        # Verify file was copied
        from pathlib import Path
        assert Path(entry["published_path"]).exists()

    def test_publish_resolves_path_from_mission(self, setup):
        """D-145 §3: Server-side resolution, no caller-supplied path."""
        ps, ms, pid, tmp_path = setup
        entry = ps.publish_artifact(pid, "mis_001", "art_001")
        assert "result.json" in entry["published_path"]
        assert entry["source_path"].endswith("result.json")

    def test_publish_404_mission_not_found(self, setup):
        ps, ms, pid, _ = setup
        with pytest.raises(ProjectStoreError, match="Mission not found"):
            ps.publish_artifact(pid, "mis_nonexistent", "art_001")

    def test_publish_422_mission_not_linked(self, setup):
        ps, ms, pid, tmp_path = setup
        # Create unlinked mission
        ms.record({
            "id": "mis_unlinked",
            "goal": "unlinked",
            "status": "completed",
            "project_id": None,
            "tokens": 0, "duration": 0, "stages": 0,
            "tools": 0, "reworks": 0, "ts": "2026-04-06T12:00:00Z",
            "artifacts": [{"id": "art_x", "path": "/tmp/x"}],
            "stages_detail": [],
        })
        with pytest.raises(ProjectLifecycleError, match="not linked"):
            ps.publish_artifact(pid, "mis_unlinked", "art_x")

    def test_publish_404_artifact_not_found(self, setup):
        ps, ms, pid, _ = setup
        with pytest.raises(ProjectStoreError, match="Artifact.*not found"):
            ps.publish_artifact(pid, "mis_001", "art_nonexistent")

    def test_publish_404_project_not_found(self, setup):
        ps, _, _, _ = setup
        with pytest.raises(ProjectStoreError, match="Project not found"):
            ps.publish_artifact("proj_nonexistent", "mis_001", "art_001")

    def test_publish_409_workspace_not_enabled(self, tmp_path):
        ms = MissionStore(store_path=tmp_path / "m.json")
        ps = ProjectStore(store_path=tmp_path / "p.json", mission_store=ms)
        proj = ps.create("No WS")
        ps.transition_status(proj["project_id"], "active")
        ms.record({
            "id": "mis_x", "goal": "x", "status": "completed",
            "project_id": proj["project_id"],
            "tokens": 0, "duration": 0, "stages": 0,
            "tools": 0, "reworks": 0, "ts": "2026-04-06",
            "artifacts": [{"id": "a1", "path": "/tmp/x"}],
            "stages_detail": [],
        })
        with pytest.raises(ProjectStoreError, match="not enabled"):
            ps.publish_artifact(proj["project_id"], "mis_x", "a1")

    def test_publish_403_on_completed_project(self, setup):
        ps, ms, pid, _ = setup
        ps.transition_status(pid, "completed")
        with pytest.raises(ProjectLifecycleError):
            ps.publish_artifact(pid, "mis_001", "art_001")

    def test_publish_403_on_cancelled_project(self, setup):
        ps, ms, pid, _ = setup
        ps.transition_status(pid, "cancelled")
        with pytest.raises(ProjectLifecycleError):
            ps.publish_artifact(pid, "mis_001", "art_001")

    def test_publish_403_on_paused_project(self, setup):
        ps, ms, pid, _ = setup
        ps.transition_status(pid, "paused")
        with pytest.raises(ProjectLifecycleError):
            ps.publish_artifact(pid, "mis_001", "art_001")

    def test_publish_tracks_in_project_record(self, setup):
        ps, ms, pid, _ = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        proj = ps.get(pid)
        assert len(proj["published_artifacts"]) == 1
        assert proj["published_artifacts"][0]["artifact_id"] == "art_001"

    def test_resolve_from_stages_detail(self, setup):
        """D-145 §3: Also check stages_detail for artifact."""
        ps, ms, pid, tmp_path = setup
        artifact_file = tmp_path / "stage_out" / "detail.txt"
        artifact_file.parent.mkdir(exist_ok=True)
        artifact_file.write_text("stage detail artifact")
        ms.record({
            "id": "mis_002", "goal": "test2", "status": "completed",
            "project_id": pid,
            "tokens": 0, "duration": 0, "stages": 1,
            "tools": 0, "reworks": 0, "ts": "2026-04-06T13:00:00Z",
            "artifacts": [],
            "stages_detail": [{
                "artifacts": [
                    {"id": "art_detail", "path": str(artifact_file)}
                ]
            }],
        })
        entry = ps.publish_artifact(pid, "mis_002", "art_detail")
        assert entry["artifact_id"] == "art_detail"


class TestListArtifacts:
    def test_list_empty(self, setup):
        ps, _, pid, _ = setup
        result = ps.list_artifacts(pid)
        assert result == []

    def test_list_after_publish(self, setup):
        ps, _, pid, _ = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        result = ps.list_artifacts(pid)
        assert len(result) == 1
        assert result[0]["artifact_id"] == "art_001"

    def test_list_filter_by_mission(self, setup):
        ps, ms, pid, tmp_path = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        # Another mission
        f2 = tmp_path / "out2" / "f.txt"
        f2.parent.mkdir(exist_ok=True)
        f2.write_text("x")
        ms.record({
            "id": "mis_002", "goal": "t2", "status": "completed",
            "project_id": pid,
            "tokens": 0, "duration": 0, "stages": 0,
            "tools": 0, "reworks": 0, "ts": "2026-04-06T14:00:00Z",
            "artifacts": [{"id": "art_002", "path": str(f2)}],
            "stages_detail": [],
        })
        ps.publish_artifact(pid, "mis_002", "art_002")
        filtered = ps.list_artifacts(pid, mission_id="mis_001")
        assert len(filtered) == 1
        assert filtered[0]["mission_id"] == "mis_001"

    def test_list_404_project_not_found(self, setup):
        ps, _, _, _ = setup
        with pytest.raises(ProjectStoreError, match="not found"):
            ps.list_artifacts("proj_nonexistent")


class TestUnpublishArtifact:
    def test_unpublish_removes_file(self, setup):
        ps, _, pid, _ = setup
        entry = ps.publish_artifact(pid, "mis_001", "art_001")
        from pathlib import Path
        assert Path(entry["published_path"]).exists()
        removed = ps.unpublish_artifact(pid, "art_001")
        assert removed is not None
        assert not Path(entry["published_path"]).exists()

    def test_unpublish_original_intact(self, setup):
        ps, _, pid, _ = setup
        entry = ps.publish_artifact(pid, "mis_001", "art_001")
        from pathlib import Path
        ps.unpublish_artifact(pid, "art_001")
        assert Path(entry["source_path"]).exists()

    def test_unpublish_returns_none_not_found(self, setup):
        ps, _, pid, _ = setup
        result = ps.unpublish_artifact(pid, "art_nonexistent")
        assert result is None

    def test_unpublish_403_on_completed_project(self, setup):
        ps, _, pid, _ = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        ps.transition_status(pid, "completed")
        with pytest.raises(ProjectLifecycleError, match="immutable"):
            ps.unpublish_artifact(pid, "art_001")

    def test_unpublish_403_on_cancelled_project(self, setup):
        ps, _, pid, _ = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        ps.transition_status(pid, "cancelled")
        with pytest.raises(ProjectLifecycleError, match="immutable"):
            ps.unpublish_artifact(pid, "art_001")

    def test_unpublish_403_on_archived_project(self, setup):
        ps, _, pid, _ = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        ps.transition_status(pid, "completed")
        ps.transition_status(pid, "archived")
        with pytest.raises(ProjectLifecycleError, match="immutable"):
            ps.unpublish_artifact(pid, "art_001")

    def test_unpublish_updates_record(self, setup):
        ps, _, pid, _ = setup
        ps.publish_artifact(pid, "mis_001", "art_001")
        assert len(ps.list_artifacts(pid)) == 1
        ps.unpublish_artifact(pid, "art_001")
        assert len(ps.list_artifacts(pid)) == 0
