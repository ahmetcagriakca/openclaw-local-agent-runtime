"""Tests for ProjectStore — D-144 §2, §6.

Task 73.9: CRUD + atomic write + FSM enforcement.
"""
import json

import pytest

from persistence.project_store import (
    ProjectStore,
    ProjectStoreError,
    generate_project_id,
)


@pytest.fixture
def tmp_store(tmp_path):
    """Create a ProjectStore with temp file."""
    return ProjectStore(store_path=tmp_path / "projects.json")


@pytest.fixture
def store_with_missions(tmp_path):
    """ProjectStore with a mock mission store."""
    from persistence.mission_store import MissionStore

    ms = MissionStore(store_path=tmp_path / "missions.json")
    ps = ProjectStore(
        store_path=tmp_path / "projects.json",
        mission_store=ms,
    )
    return ps, ms


class TestGenerateProjectId:
    def test_prefix(self):
        pid = generate_project_id()
        assert pid.startswith("proj_")

    def test_unique(self):
        ids = {generate_project_id() for _ in range(100)}
        assert len(ids) == 100


class TestProjectStoreCreate:
    def test_create_basic(self, tmp_store):
        proj = tmp_store.create("Test Project")
        assert proj["name"] == "Test Project"
        assert proj["status"] == "draft"
        assert proj["project_id"].startswith("proj_")
        assert proj["owner"] == "operator"

    def test_create_with_fields(self, tmp_store):
        proj = tmp_store.create(
            name="My Project",
            description="A test",
            owner="akca",
        )
        assert proj["description"] == "A test"
        assert proj["owner"] == "akca"

    def test_create_persists(self, tmp_path):
        path = tmp_path / "projects.json"
        store = ProjectStore(store_path=path)
        proj = store.create("Persist Test")

        # Reload from disk
        store2 = ProjectStore(store_path=path)
        loaded = store2.get(proj["project_id"])
        assert loaded is not None
        assert loaded["name"] == "Persist Test"

    def test_atomic_write(self, tmp_path):
        path = tmp_path / "projects.json"
        store = ProjectStore(store_path=path)
        store.create("Atomic Test")

        data = json.loads(path.read_text(encoding="utf-8"))
        assert "version" in data
        assert "updated_at" in data
        assert "projects" in data


class TestProjectStoreGet:
    def test_get_existing(self, tmp_store):
        proj = tmp_store.create("Get Test")
        result = tmp_store.get(proj["project_id"])
        assert result is not None
        assert result["name"] == "Get Test"

    def test_get_nonexistent(self, tmp_store):
        result = tmp_store.get("proj_nonexistent")
        assert result is None

    def test_get_returns_copy(self, tmp_store):
        proj = tmp_store.create("Copy Test")
        result = tmp_store.get(proj["project_id"])
        result["name"] = "Modified"
        original = tmp_store.get(proj["project_id"])
        assert original["name"] == "Copy Test"


class TestProjectStoreList:
    def test_list_empty(self, tmp_store):
        items, total = tmp_store.list()
        assert items == []
        assert total == 0

    def test_list_all(self, tmp_store):
        tmp_store.create("A")
        tmp_store.create("B")
        items, total = tmp_store.list()
        assert total == 2
        assert len(items) == 2

    def test_list_filter_status(self, tmp_store):
        tmp_store.create("Draft1")
        p2 = tmp_store.create("Draft2")
        tmp_store.transition_status(p2["project_id"], "active")
        items, total = tmp_store.list(status=["active"])
        assert total == 1
        assert items[0]["name"] == "Draft2"

    def test_list_search(self, tmp_store):
        tmp_store.create("Alpha Project")
        tmp_store.create("Beta Project")
        items, total = tmp_store.list(search="alpha")
        assert total == 1
        assert items[0]["name"] == "Alpha Project"

    def test_list_pagination(self, tmp_store):
        for i in range(5):
            tmp_store.create(f"Project {i}")
        items, total = tmp_store.list(limit=2, offset=0)
        assert total == 5
        assert len(items) == 2


class TestProjectStoreUpdate:
    def test_update_name(self, tmp_store):
        proj = tmp_store.create("Original")
        updated = tmp_store.update(proj["project_id"], name="Renamed")
        assert updated["name"] == "Renamed"

    def test_update_description(self, tmp_store):
        proj = tmp_store.create("Test")
        updated = tmp_store.update(
            proj["project_id"], description="New desc")
        assert updated["description"] == "New desc"

    def test_update_nonexistent(self, tmp_store):
        with pytest.raises(ProjectStoreError, match="not found"):
            tmp_store.update("proj_fake", name="Fail")

    def test_update_ignores_unknown_fields(self, tmp_store):
        proj = tmp_store.create("Test")
        updated = tmp_store.update(
            proj["project_id"], name="OK", badfield="ignored")
        assert updated["name"] == "OK"
        assert "badfield" not in updated


class TestProjectStoreCount:
    def test_count_empty(self, tmp_store):
        assert tmp_store.count == 0

    def test_count_after_create(self, tmp_store):
        tmp_store.create("A")
        tmp_store.create("B")
        assert tmp_store.count == 2


class TestProjectStoreClear:
    def test_clear(self, tmp_store):
        tmp_store.create("A")
        tmp_store.create("B")
        assert tmp_store.count == 2
        tmp_store.clear()
        assert tmp_store.count == 0
