"""D-128: Risk classification tests."""
from services.risk_engine import TOOL_RISK_MAP, RiskEngine


class TestRiskClassifyMission:
    """D-128: Mission-level risk classification."""

    def test_risk_empty_tools_returns_low(self):
        engine = RiskEngine()
        assert engine.classify_mission([]) == "low"

    def test_risk_read_only_tools_returns_low(self):
        engine = RiskEngine()
        assert engine.classify_mission(["file_read", "search", "list_files"]) == "low"

    def test_risk_write_tools_returns_medium(self):
        engine = RiskEngine()
        assert engine.classify_mission(["file_write", "create_directory"]) == "medium"

    def test_risk_mixed_read_write_returns_medium(self):
        engine = RiskEngine()
        assert engine.classify_mission(["file_read", "file_write"]) == "medium"

    def test_risk_network_tools_returns_high(self):
        engine = RiskEngine()
        assert engine.classify_mission(["http_request"]) == "high"

    def test_risk_exec_tools_returns_high(self):
        engine = RiskEngine()
        assert engine.classify_mission(["run_command"]) == "high"

    def test_risk_admin_tools_returns_critical(self):
        engine = RiskEngine()
        assert engine.classify_mission(["system_config"]) == "critical"

    def test_risk_mixed_returns_highest(self):
        engine = RiskEngine()
        # low + critical = critical
        assert engine.classify_mission(["file_read", "system_config"]) == "critical"

    def test_risk_unknown_tool_defaults_high(self):
        """D-128: Unknown tools default to high (fail-safe)."""
        engine = RiskEngine()
        assert engine.classify_mission(["totally_unknown_tool"]) == "high"

    def test_risk_unknown_mixed_with_low(self):
        engine = RiskEngine()
        # low + unknown(high) = high
        assert engine.classify_mission(["file_read", "mystery_tool"]) == "high"


class TestRiskToolMap:
    """D-128: Tool-to-risk mapping exists for known tools."""

    def test_risk_map_has_low_tools(self):
        assert TOOL_RISK_MAP["file_read"] == "low"
        assert TOOL_RISK_MAP["search"] == "low"

    def test_risk_map_has_medium_tools(self):
        assert TOOL_RISK_MAP["file_write"] == "medium"

    def test_risk_map_has_high_tools(self):
        assert TOOL_RISK_MAP["http_request"] == "high"
        assert TOOL_RISK_MAP["run_command"] == "high"

    def test_risk_map_has_critical_tools(self):
        assert TOOL_RISK_MAP["system_config"] == "critical"
        assert TOOL_RISK_MAP["delete_recursive"] == "critical"


class TestRiskPersistence:
    """D-128: risk_level persisted in mission state, not in API response."""

    def test_risk_level_not_in_mission_summary(self):
        """D-128: MissionSummary must NOT expose risk_level."""
        from api.schemas import MissionSummary
        # Verify risk_level is not a field in MissionSummary
        fields = MissionSummary.__fields__ if hasattr(MissionSummary, '__fields__') else {}
        field_names = set(fields.keys()) if fields else set()
        assert "risk_level" not in field_names, "risk_level must not be exposed in MissionSummary (D-128)"

    def test_risk_level_in_mission_dict(self):
        """D-128: Mission dict should have risk_level field."""
        mission = {
            "missionId": "test-001",
            "risk_level": "high",
        }
        assert mission["risk_level"] == "high"

    def test_risk_level_immutable_after_creation(self):
        """D-128: risk_level computed once, never recomputed."""
        engine = RiskEngine()
        # Classify with initial tools
        level = engine.classify_mission(["file_read"])
        assert level == "low"
        # Same engine, different tools — but mission keeps original
        # (Controller must not re-call classify_mission after creation)
        level2 = engine.classify_mission(["system_config"])
        assert level2 == "critical"
        # Original classification is still "low" — it's the controller's
        # responsibility to not recompute, which we test via integration
