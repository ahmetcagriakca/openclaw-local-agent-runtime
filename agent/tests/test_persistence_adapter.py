"""Tests for MissionPersistenceAdapter — B-139 extraction from controller."""
import json
import os

# Add agent to path
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mission.persistence_adapter import MissionPersistenceAdapter


@pytest.fixture
def tmp_missions_dir(tmp_path):
    d = tmp_path / "missions"
    d.mkdir()
    return str(d)


@pytest.fixture
def adapter(tmp_missions_dir):
    return MissionPersistenceAdapter(missions_dir=tmp_missions_dir)


class TestAtomicWriteJson:
    def test_writes_valid_json(self, tmp_missions_dir):
        path = os.path.join(tmp_missions_dir, "test.json")
        data = {"key": "value", "num": 42}
        MissionPersistenceAdapter._atomic_write_json(path, data)

        with open(path, encoding="utf-8") as f:
            result = json.load(f)
        assert result == data

    def test_creates_parent_dirs(self, tmp_path):
        deep = str(tmp_path / "a" / "b" / "c" / "test.json")
        MissionPersistenceAdapter._atomic_write_json(deep, {"ok": True})
        assert os.path.exists(deep)

    def test_overwrites_existing(self, tmp_missions_dir):
        path = os.path.join(tmp_missions_dir, "test.json")
        MissionPersistenceAdapter._atomic_write_json(path, {"v": 1})
        MissionPersistenceAdapter._atomic_write_json(path, {"v": 2})
        with open(path, encoding="utf-8") as f:
            assert json.load(f)["v"] == 2


class TestSaveMission:
    def test_save_and_load(self, adapter, tmp_missions_dir):
        mission = {"missionId": "m-001", "status": "running", "stages": []}
        adapter.save_mission(mission)

        path = os.path.join(tmp_missions_dir, "m-001.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            loaded = json.load(f)
        assert loaded["missionId"] == "m-001"
        assert loaded["status"] == "running"

    def test_save_updates_in_place(self, adapter, tmp_missions_dir):
        mission = {"missionId": "m-002", "status": "running"}
        adapter.save_mission(mission)
        mission["status"] = "completed"
        adapter.save_mission(mission)

        path = os.path.join(tmp_missions_dir, "m-002.json")
        with open(path, encoding="utf-8") as f:
            assert json.load(f)["status"] == "completed"


class TestPersistMissionState:
    def test_persist_state(self, adapter, tmp_missions_dir):
        class FakeState:
            mission_id = "m-state-01"
            def to_dict(self):
                return {"mission_id": self.mission_id, "status": "running"}

        adapter.persist_mission_state(FakeState())
        path = os.path.join(tmp_missions_dir, "m-state-01-state.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        assert data["status"] == "running"


class TestSaveTokenReport:
    def test_basic_token_report(self, adapter, tmp_missions_dir):
        mission = {
            "missionId": "m-tok-01",
            "status": "completed",
            "stages": [
                {
                    "status": "completed",
                    "token_report": {
                        "stages": [{"stage": "s1", "tokens_consumed": 100, "tool_calls": 2, "pct_of_total": 0}],
                        "total_tokens": 100,
                        "total_tool_calls": 2,
                        "truncations": 0,
                        "blocks": 0,
                    }
                }
            ]
        }
        adapter.save_token_report(mission)

        path = os.path.join(tmp_missions_dir, "m-tok-01-token-report.json")
        assert os.path.exists(path)
        with open(path, encoding="utf-8") as f:
            report = json.load(f)
        assert report["total_tokens"] == 100
        assert report["total_tool_calls"] == 2

    def test_empty_mission_id_skips(self, adapter, tmp_missions_dir):
        adapter.save_token_report({"missionId": "", "stages": []})
        assert len(os.listdir(tmp_missions_dir)) == 0


class TestFindStageIndex:
    def test_finds_existing(self):
        stages = [{"id": "s-1"}, {"id": "s-2"}, {"id": "s-3"}]
        assert MissionPersistenceAdapter.find_stage_index(stages, "s-2") == 1

    def test_returns_none_for_missing(self):
        stages = [{"id": "s-1"}]
        assert MissionPersistenceAdapter.find_stage_index(stages, "s-99") is None

    def test_empty_list(self):
        assert MissionPersistenceAdapter.find_stage_index([], "s-1") is None
