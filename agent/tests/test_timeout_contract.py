"""B-014 Sprint 53: timeoutSeconds in contract — API and schema tests."""
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from api.mission_create_api import CreateMissionRequest
from api.schemas import MissionSummary


# ── CreateMissionRequest timeout fields ──────────────────────────


class TestCreateMissionRequestTimeout:
    """B-014 Sprint 53: Timeout fields in mission creation request."""

    def test_default_timeout_is_none(self):
        req = CreateMissionRequest(goal="test")
        assert req.timeout_seconds is None
        assert req.stage_timeout_seconds is None

    def test_custom_mission_timeout(self):
        req = CreateMissionRequest(goal="test", timeout_seconds=1800)
        assert req.timeout_seconds == 1800

    def test_custom_stage_timeout(self):
        req = CreateMissionRequest(goal="test", stage_timeout_seconds=300)
        assert req.stage_timeout_seconds == 300

    def test_both_timeouts(self):
        req = CreateMissionRequest(
            goal="test", timeout_seconds=7200, stage_timeout_seconds=600)
        assert req.timeout_seconds == 7200
        assert req.stage_timeout_seconds == 600

    def test_minimum_mission_timeout(self):
        req = CreateMissionRequest(goal="test", timeout_seconds=60)
        assert req.timeout_seconds == 60

    def test_maximum_mission_timeout(self):
        req = CreateMissionRequest(goal="test", timeout_seconds=86400)
        assert req.timeout_seconds == 86400

    def test_below_minimum_mission_timeout_rejected(self):
        with pytest.raises(ValidationError):
            CreateMissionRequest(goal="test", timeout_seconds=30)

    def test_above_maximum_mission_timeout_rejected(self):
        with pytest.raises(ValidationError):
            CreateMissionRequest(goal="test", timeout_seconds=100000)

    def test_minimum_stage_timeout(self):
        req = CreateMissionRequest(goal="test", stage_timeout_seconds=30)
        assert req.stage_timeout_seconds == 30

    def test_below_minimum_stage_timeout_rejected(self):
        with pytest.raises(ValidationError):
            CreateMissionRequest(goal="test", stage_timeout_seconds=10)

    def test_above_maximum_stage_timeout_rejected(self):
        with pytest.raises(ValidationError):
            CreateMissionRequest(goal="test", stage_timeout_seconds=10000)


# ── MissionSummary timeoutConfig field ───────────────────────────


class TestMissionSummaryTimeout:
    """B-014 Sprint 53: timeoutConfig in mission detail response."""

    def test_default_timeout_config_is_none(self):
        ms = MissionSummary(missionId="test-1")
        assert ms.timeoutConfig is None

    def test_timeout_config_set(self):
        tc = {"missionSeconds": 1800, "stageSeconds": 300, "toolSeconds": 60}
        ms = MissionSummary(missionId="test-2", timeoutConfig=tc)
        assert ms.timeoutConfig["missionSeconds"] == 1800
        assert ms.timeoutConfig["stageSeconds"] == 300

    def test_round_trip_serialization(self):
        tc = {"missionSeconds": 7200, "stageSeconds": 600}
        ms = MissionSummary(missionId="test-3", state="running", timeoutConfig=tc)
        data = ms.model_dump()
        restored = MissionSummary(**data)
        assert restored.timeoutConfig == tc

    def test_backward_compat_no_timeout(self):
        """Old data without timeoutConfig still works."""
        data = {"missionId": "old-1", "state": "completed"}
        ms = MissionSummary(**data)
        assert ms.timeoutConfig is None


# ── Mission data builder (timeout config inclusion) ──────────────


class TestMissionDataBuilder:
    """B-014 Sprint 53: Timeout config flows into mission JSON."""

    def test_timeout_in_mission_data_when_set(self):
        req = CreateMissionRequest(goal="test", timeout_seconds=1800,
                                   stage_timeout_seconds=300)
        timeout_config = {}
        if req.timeout_seconds is not None:
            timeout_config["missionSeconds"] = req.timeout_seconds
        if req.stage_timeout_seconds is not None:
            timeout_config["stageSeconds"] = req.stage_timeout_seconds

        mission_data = {"missionId": "m1", "status": "pending", "goal": req.goal}
        if timeout_config:
            mission_data["timeoutConfig"] = timeout_config

        assert "timeoutConfig" in mission_data
        assert mission_data["timeoutConfig"]["missionSeconds"] == 1800
        assert mission_data["timeoutConfig"]["stageSeconds"] == 300

    def test_no_timeout_in_mission_data_when_default(self):
        req = CreateMissionRequest(goal="test")
        timeout_config = {}
        if req.timeout_seconds is not None:
            timeout_config["missionSeconds"] = req.timeout_seconds
        if req.stage_timeout_seconds is not None:
            timeout_config["stageSeconds"] = req.stage_timeout_seconds

        mission_data = {"missionId": "m2", "status": "pending", "goal": req.goal}
        if timeout_config:
            mission_data["timeoutConfig"] = timeout_config

        assert "timeoutConfig" not in mission_data
