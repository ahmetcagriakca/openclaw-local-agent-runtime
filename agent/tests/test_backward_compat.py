"""Tests for backward compatibility — D-144 §12.

Task 73.8: project_id=null missions behave identically. Zero-disruption rule.
"""
import pytest

from persistence.mission_store import MissionStore


@pytest.fixture
def mission_store(tmp_path):
    return MissionStore(store_path=tmp_path / "missions.json")


class TestProjectIdNullDefault:
    """D-144 §12: Missions without project_id default to null."""

    def test_new_mission_has_project_id_null(self, mission_store):
        """New missions created without project_id get null."""
        mission_store.record({
            "id": "mis-1",
            "goal": "standalone task",
            "status": "completed",
        })
        mission = mission_store.get("mis-1")
        assert mission["project_id"] is None

    def test_explicit_null_project_id(self, mission_store):
        mission_store.record({
            "id": "mis-2",
            "goal": "explicit null",
            "status": "completed",
            "project_id": None,
        })
        mission = mission_store.get("mis-2")
        assert mission["project_id"] is None

    def test_explicit_project_id(self, mission_store):
        mission_store.record({
            "id": "mis-3",
            "goal": "linked",
            "status": "running",
            "project_id": "proj_abc123",
        })
        mission = mission_store.get("mis-3")
        assert mission["project_id"] == "proj_abc123"


class TestMissionCRUDUnchanged:
    """D-144 §12: Core mission CRUD operations unchanged by project_id."""

    def test_record_and_get(self, mission_store):
        mission_store.record({
            "id": "mis-crud-1",
            "goal": "basic CRUD",
            "status": "completed",
            "tokens": 500,
        })
        mission = mission_store.get("mis-crud-1")
        assert mission is not None
        assert mission["goal"] == "basic CRUD"
        assert mission["tokens"] == 500

    def test_list_without_project_filter(self, mission_store):
        for i in range(3):
            mission_store.record({
                "id": f"mis-list-{i}",
                "goal": f"mission {i}",
                "status": "completed",
            })
        missions, total = mission_store.list()
        assert total == 3

    def test_list_filter_by_status(self, mission_store):
        mission_store.record({"id": "m1", "goal": "a", "status": "completed"})
        mission_store.record({"id": "m2", "goal": "b", "status": "failed"})
        items, total = mission_store.list(status=["completed"])
        assert total == 1
        assert items[0]["status"] == "completed"

    def test_summary_unchanged(self, mission_store):
        mission_store.record({
            "id": "m-sum",
            "goal": "summary test",
            "status": "completed",
            "tokens": 1000,
        })
        summary = mission_store.summary()
        assert summary["total_missions"] == 1
        assert summary["completed"] == 1
        assert summary["total_tokens"] == 1000

    def test_count_property(self, mission_store):
        assert mission_store.count == 0
        mission_store.record({"id": "m1", "goal": "a", "status": "completed"})
        assert mission_store.count == 1

    def test_clear(self, mission_store):
        mission_store.record({"id": "m1", "goal": "a", "status": "completed"})
        mission_store.clear()
        assert mission_store.count == 0


class TestMixedProjectMissions:
    """Standalone and project-linked missions coexist."""

    def test_mixed_list(self, mission_store):
        mission_store.record({
            "id": "standalone",
            "goal": "no project",
            "status": "completed",
        })
        mission_store.record({
            "id": "linked",
            "goal": "with project",
            "status": "completed",
            "project_id": "proj_xyz",
        })

        missions, total = mission_store.list()
        assert total == 2

        standalone = mission_store.get("standalone")
        linked = mission_store.get("linked")
        assert standalone["project_id"] is None
        assert linked["project_id"] == "proj_xyz"

    def test_summary_includes_both(self, mission_store):
        mission_store.record({
            "id": "s1",
            "goal": "standalone",
            "status": "completed",
            "tokens": 100,
        })
        mission_store.record({
            "id": "l1",
            "goal": "linked",
            "status": "completed",
            "tokens": 200,
            "project_id": "proj_xyz",
        })

        summary = mission_store.summary()
        assert summary["total_missions"] == 2
        assert summary["total_tokens"] == 300


class TestPersistenceRoundTrip:
    """project_id survives save/load cycle."""

    def test_project_id_persisted(self, tmp_path):
        path = tmp_path / "missions.json"
        store1 = MissionStore(store_path=path)
        store1.record({
            "id": "persist-test",
            "goal": "roundtrip",
            "status": "completed",
            "project_id": "proj_persist",
        })

        store2 = MissionStore(store_path=path)
        mission = store2.get("persist-test")
        assert mission["project_id"] == "proj_persist"

    def test_null_project_id_persisted(self, tmp_path):
        path = tmp_path / "missions.json"
        store1 = MissionStore(store_path=path)
        store1.record({
            "id": "null-test",
            "goal": "no project",
            "status": "completed",
        })

        store2 = MissionStore(store_path=path)
        mission = store2.get("null-test")
        assert mission["project_id"] is None
