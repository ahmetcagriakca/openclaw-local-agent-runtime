"""Tests for B-140: Hard per-mission token budget enforcement."""
import os
import sys
from unittest.mock import patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from mission.policy_context import PolicyContext, build_policy_context
from mission.policy_engine import PolicyEngine

# ── PolicyContext budget fields ─────────────────────────────────

class TestPolicyContextBudget:
    def test_to_dict_includes_budget(self):
        ctx = PolicyContext(total_tokens=50000, max_token_budget=200000)
        d = ctx.to_dict()
        assert d["totalTokens"] == 50000
        assert d["maxTokenBudget"] == 200000

    def test_from_dict_budget(self):
        data = {"totalTokens": 75000, "maxTokenBudget": 100000}
        ctx = PolicyContext.from_dict(data)
        assert ctx.total_tokens == 75000
        assert ctx.max_token_budget == 100000

    def test_defaults_zero(self):
        ctx = PolicyContext()
        assert ctx.total_tokens == 0
        assert ctx.max_token_budget == 0

    def test_build_policy_context_populates_budget(self):
        mission = {
            "cumulativeTokens": 150000,
            "maxTokenBudget": 200000,
            "risk_level": "medium",
            "stages": [],
            "timeoutConfig": {},
        }
        with patch("mission.policy_context.check_wmcp_availability") as mock_wmcp:
            mock_wmcp.return_value = type("DS", (), {
                "name": "wmcp", "status": "unreachable",
                "last_checked": None, "error": None,
                "to_dict": lambda self: {"name": "wmcp", "status": "unreachable"}
            })()
            ctx = build_policy_context(mission, 0.0)
        assert ctx.total_tokens == 150000
        assert ctx.max_token_budget == 200000

    def test_build_policy_context_no_budget(self):
        mission = {"risk_level": "medium", "stages": [], "timeoutConfig": {}}
        with patch("mission.policy_context.check_wmcp_availability") as mock_wmcp:
            mock_wmcp.return_value = type("DS", (), {
                "name": "wmcp", "status": "unreachable",
                "last_checked": None, "error": None,
                "to_dict": lambda self: {"name": "wmcp", "status": "unreachable"}
            })()
            ctx = build_policy_context(mission, 0.0)
        assert ctx.total_tokens == 0
        assert ctx.max_token_budget == 0


# ── PolicyEngine budget condition ───────────────────────────────

class TestPolicyEngineBudget:
    def test_token_budget_exceeded_denies(self):
        engine = PolicyEngine.__new__(PolicyEngine)
        engine._rules = []
        engine._load_errors = []
        # Manually create the condition match
        assert engine._matches(
            {"token_budget_exceeded": True},
            {"totalTokens": 200000, "maxTokenBudget": 200000},
            {}, None
        ) is True

    def test_token_budget_not_exceeded(self):
        engine = PolicyEngine.__new__(PolicyEngine)
        engine._rules = []
        assert engine._matches(
            {"token_budget_exceeded": True},
            {"totalTokens": 100000, "maxTokenBudget": 200000},
            {}, None
        ) is False

    def test_token_budget_no_limit_set(self):
        engine = PolicyEngine.__new__(PolicyEngine)
        engine._rules = []
        assert engine._matches(
            {"token_budget_exceeded": True},
            {"totalTokens": 999999, "maxTokenBudget": 0},
            {}, None
        ) is False

    def test_token_budget_warning_80pct(self):
        engine = PolicyEngine.__new__(PolicyEngine)
        engine._rules = []
        assert engine._matches(
            {"token_budget_warning": True},
            {"totalTokens": 160000, "maxTokenBudget": 200000},
            {}, None
        ) is True

    def test_token_budget_warning_below_80pct(self):
        engine = PolicyEngine.__new__(PolicyEngine)
        engine._rules = []
        assert engine._matches(
            {"token_budget_warning": True},
            {"totalTokens": 100000, "maxTokenBudget": 200000},
            {}, None
        ) is False

    def test_token_budget_warning_no_limit(self):
        engine = PolicyEngine.__new__(PolicyEngine)
        engine._rules = []
        assert engine._matches(
            {"token_budget_warning": True},
            {"totalTokens": 999999, "maxTokenBudget": 0},
            {}, None
        ) is False


# ── Controller budget methods ───────────────────────────────────

class TestControllerBudget:
    def test_update_mission_budget(self):
        from mission.controller import MissionController
        mission = {
            "stages": [
                {"status": "completed", "token_report": {"total_tokens": 5000}},
                {"status": "completed", "token_report": {"total_tokens": 3000}},
                {"status": "running", "token_report": {"total_tokens": 1000}},
            ]
        }
        total = MissionController._update_mission_budget(mission)
        assert total == 8000
        assert mission["cumulativeTokens"] == 8000

    def test_update_mission_budget_no_token_report(self):
        from mission.controller import MissionController
        mission = {
            "stages": [
                {"status": "completed"},
                {"status": "completed", "token_report": {"total_tokens": 2000}},
            ]
        }
        total = MissionController._update_mission_budget(mission)
        assert total == 2000

    def test_update_mission_budget_empty(self):
        from mission.controller import MissionController
        mission = {"stages": []}
        total = MissionController._update_mission_budget(mission)
        assert total == 0

    def test_default_token_budget_trivial(self):
        from mission.controller import MissionController
        assert MissionController._default_token_budget("trivial") == 50_000

    def test_default_token_budget_standard(self):
        from mission.controller import MissionController
        assert MissionController._default_token_budget("standard") == 200_000

    def test_default_token_budget_complex(self):
        from mission.controller import MissionController
        assert MissionController._default_token_budget("complex") == 500_000

    def test_default_token_budget_critical(self):
        from mission.controller import MissionController
        assert MissionController._default_token_budget("critical") == 1_000_000

    def test_default_token_budget_unknown(self):
        from mission.controller import MissionController
        assert MissionController._default_token_budget("unknown") is None


# ── Schema ──────────────────────────────────────────────────────

class TestSchemaFields:
    def test_mission_summary_has_budget_fields(self):
        from api.schemas import MissionSummary
        m = MissionSummary(missionId="test-1", cumulativeTokens=50000, maxTokenBudget=200000)
        assert m.cumulativeTokens == 50000
        assert m.maxTokenBudget == 200000

    def test_mission_summary_defaults(self):
        from api.schemas import MissionSummary
        m = MissionSummary(missionId="test-2")
        assert m.cumulativeTokens == 0
        assert m.maxTokenBudget is None
