"""Tests for Project Workspace — D-145 §1.

Task 74.8: Workspace enable, directory structure, metadata.
"""
import pytest

from persistence.project_store import (
    ProjectLifecycleError,
    ProjectStore,
    ProjectStoreError,
)


@pytest.fixture
def tmp_store(tmp_path):
    """ProjectStore with temp file."""
    return ProjectStore(store_path=tmp_path / "projects.json")


@pytest.fixture
def store_with_project(tmp_path):
    """ProjectStore with a draft project."""
    store = ProjectStore(store_path=tmp_path / "projects.json")
    proj = store.create("Workspace Test")
    return store, proj, tmp_path


class TestEnableWorkspace:
    def test_enable_creates_directories(self, store_with_project):
        store, proj, tmp_path = store_with_project
        projects_root = tmp_path / "projects"
        result = store.enable_workspace(proj["project_id"],
                                         projects_root=projects_root)
        assert result["workspace_root"] is not None
        assert result["artifact_root"] is not None
        assert result["shared_root"] is not None
        # Verify directories exist
        from pathlib import Path
        assert Path(result["workspace_root"]).is_dir()
        assert Path(result["artifact_root"]).is_dir()
        assert Path(result["shared_root"]).is_dir()
        assert (Path(result["shared_root"]) / "decisions").is_dir()
        assert (Path(result["shared_root"]) / "notes").is_dir()
        assert (Path(result["shared_root"]) / "briefs").is_dir()

    def test_enable_409_already_enabled(self, store_with_project):
        store, proj, tmp_path = store_with_project
        projects_root = tmp_path / "projects"
        store.enable_workspace(proj["project_id"],
                                projects_root=projects_root)
        with pytest.raises(ProjectStoreError, match="already enabled"):
            store.enable_workspace(proj["project_id"],
                                    projects_root=projects_root)

    def test_enable_403_paused_project(self, store_with_project):
        store, proj, tmp_path = store_with_project
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.transition_status(pid, "paused")
        with pytest.raises(ProjectLifecycleError):
            store.enable_workspace(pid, projects_root=tmp_path / "p")

    def test_enable_403_completed_project(self, store_with_project):
        store, proj, tmp_path = store_with_project
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.transition_status(pid, "completed")
        with pytest.raises(ProjectLifecycleError):
            store.enable_workspace(pid, projects_root=tmp_path / "p")

    def test_enable_403_cancelled_project(self, store_with_project):
        store, proj, tmp_path = store_with_project
        pid = proj["project_id"]
        store.transition_status(pid, "cancelled")
        with pytest.raises(ProjectLifecycleError):
            store.enable_workspace(pid, projects_root=tmp_path / "p")

    def test_enable_403_archived_project(self, store_with_project):
        store, proj, tmp_path = store_with_project
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.transition_status(pid, "completed")
        store.transition_status(pid, "archived")
        with pytest.raises(ProjectLifecycleError):
            store.enable_workspace(pid, projects_root=tmp_path / "p")

    def test_enable_404_not_found(self, tmp_store):
        with pytest.raises(ProjectStoreError, match="not found"):
            tmp_store.enable_workspace("proj_nonexistent",
                                        projects_root="/tmp/p")

    def test_enable_on_active_project(self, store_with_project):
        store, proj, tmp_path = store_with_project
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        result = store.enable_workspace(pid,
                                         projects_root=tmp_path / "p")
        assert result["workspace_root"] is not None

    def test_enable_updates_project_record(self, store_with_project):
        store, proj, tmp_path = store_with_project
        pid = proj["project_id"]
        store.enable_workspace(pid, projects_root=tmp_path / "p")
        updated = store.get(pid)
        assert updated["workspace_root"] is not None
        assert updated["artifact_root"] is not None
        assert updated["shared_root"] is not None

    def test_workspace_persists_after_reload(self, tmp_path):
        store_path = tmp_path / "projects.json"
        store = ProjectStore(store_path=store_path)
        proj = store.create("Persist Test")
        store.enable_workspace(proj["project_id"],
                                projects_root=tmp_path / "p")
        # Reload
        store2 = ProjectStore(store_path=store_path)
        proj2 = store2.get(proj["project_id"])
        assert proj2["workspace_root"] is not None


class TestGetWorkspace:
    def test_get_workspace_not_enabled(self, store_with_project):
        store, proj, _ = store_with_project
        ws = store.get_workspace(proj["project_id"])
        assert ws["enabled"] is False
        assert ws["workspace_root"] is None

    def test_get_workspace_enabled(self, store_with_project):
        store, proj, tmp_path = store_with_project
        store.enable_workspace(proj["project_id"],
                                projects_root=tmp_path / "p")
        ws = store.get_workspace(proj["project_id"])
        assert ws["enabled"] is True
        assert ws["workspace_root"] is not None
        assert ws["artifact_root"] is not None
        assert ws["shared_root"] is not None

    def test_get_workspace_404(self, tmp_store):
        assert tmp_store.get_workspace("proj_nonexistent") is None
