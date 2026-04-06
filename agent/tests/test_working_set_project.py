"""Tests for WorkingSet project path injection — D-145 §2.

Task 74.9: Project read-only paths in WorkingSet.
"""
import pytest

from mission.controller import MissionController


@pytest.fixture
def controller():
    return MissionController.__new__(MissionController)


class TestBuildDefaultWorkingSetProjectInjection:
    """D-145 §2: Project paths injected as read-only."""

    def test_no_mission_no_project_paths(self, controller):
        ws = controller._build_default_working_set("s1", "developer")
        assert ws.files.read_only == []

    def test_mission_without_project_id(self, controller):
        mission = {"id": "m1", "goal": "test", "status": "executing"}
        ws = controller._build_default_working_set("s1", "developer",
                                                     mission=mission)
        assert ws.files.read_only == []

    def test_mission_with_project_id_no_store(self, controller):
        """When project store is not available, returns empty paths."""
        mission = {"id": "m1", "project_id": "proj_abc", "status": "executing"}
        ws = controller._build_default_working_set("s1", "developer",
                                                     mission=mission)
        # Should gracefully return empty (store not initialized)
        assert ws.files.read_only == []

    def test_project_paths_injected_when_available(self, controller, tmp_path):
        """Full integration: project store → workspace → injection."""
        from api.project_api import set_store
        from persistence.project_store import ProjectStore

        store = ProjectStore(store_path=tmp_path / "projects.json")
        proj = store.create("Inject Test")
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.enable_workspace(pid, projects_root=tmp_path / "p")

        set_store(store)
        try:
            mission = {"id": "m1", "project_id": pid, "status": "executing"}
            ws = controller._build_default_working_set("s1", "developer",
                                                         mission=mission)
            assert len(ws.files.read_only) == 3
            paths = ws.files.read_only
            assert any("shared" in p for p in paths)
            assert any("artifacts" in p for p in paths)
            assert any("workspace" in p for p in paths)
        finally:
            set_store(None)

    def test_project_paths_not_injected_for_inactive_project(
            self, controller, tmp_path):
        """D-145 §2: Inactive project → no injection."""
        from api.project_api import set_store
        from persistence.project_store import ProjectStore

        store = ProjectStore(store_path=tmp_path / "projects.json")
        proj = store.create("Inactive Test")
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.enable_workspace(pid, projects_root=tmp_path / "p")
        store.transition_status(pid, "completed")

        set_store(store)
        try:
            mission = {"id": "m1", "project_id": pid, "status": "executing"}
            ws = controller._build_default_working_set("s1", "developer",
                                                         mission=mission)
            assert ws.files.read_only == []
        finally:
            set_store(None)

    def test_project_paths_not_injected_without_workspace(
            self, controller, tmp_path):
        """D-145 §2: No workspace → no injection."""
        from api.project_api import set_store
        from persistence.project_store import ProjectStore

        store = ProjectStore(store_path=tmp_path / "projects.json")
        proj = store.create("No WS Test")
        pid = proj["project_id"]
        store.transition_status(pid, "active")

        set_store(store)
        try:
            mission = {"id": "m1", "project_id": pid, "status": "executing"}
            ws = controller._build_default_working_set("s1", "developer",
                                                         mission=mission)
            assert ws.files.read_only == []
        finally:
            set_store(None)

    def test_project_paths_are_read_only_not_writable(
            self, controller, tmp_path):
        """D-145 §2: Project dirs must NOT appear in write paths."""
        from api.project_api import set_store
        from persistence.project_store import ProjectStore

        store = ProjectStore(store_path=tmp_path / "projects.json")
        proj = store.create("RO Test")
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.enable_workspace(pid, projects_root=tmp_path / "p")

        set_store(store)
        try:
            mission = {"id": "m1", "project_id": pid, "status": "executing"}
            ws = controller._build_default_working_set("s1", "developer",
                                                         mission=mission)
            # Verify NOT in writable paths
            assert ws.files.read_write == []
            assert ws.files.creatable == []
            for path in ws.files.read_only:
                assert path not in ws.files.generated_outputs
        finally:
            set_store(None)

    def test_project_paths_in_directory_list(self, controller, tmp_path):
        """D-145 §2: Project paths added to directory_list for listing."""
        from api.project_api import set_store
        from persistence.project_store import ProjectStore

        store = ProjectStore(store_path=tmp_path / "projects.json")
        proj = store.create("DirList Test")
        pid = proj["project_id"]
        store.transition_status(pid, "active")
        store.enable_workspace(pid, projects_root=tmp_path / "p")

        set_store(store)
        try:
            mission = {"id": "m1", "project_id": pid, "status": "executing"}
            ws = controller._build_default_working_set("s1", "developer",
                                                         mission=mission)
            # Project paths should be in directory_list
            for path in ws.files.read_only:
                assert path in ws.files.directory_list
        finally:
            set_store(None)
