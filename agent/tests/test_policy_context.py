"""B-013 + B-014: Policy context and timeout tests."""
import time
from unittest.mock import patch

from mission.mission_state import VALID_TRANSITIONS, MissionState, MissionStatus
from mission.policy_context import (
    DEFAULT_MISSION_TIMEOUT,
    DEFAULT_STAGE_TIMEOUT,
    DEFAULT_TOOL_TIMEOUT,
    CallerIdentity,
    DependencyState,
    PolicyContext,
    TimeoutConfig,
    _detect_environment,
    build_policy_context,
    check_wmcp_availability,
)

# --- B-013: PolicyContext tests ---


class TestPolicyContextDefaults:
    """B-013: PolicyContext has safe defaults for backward compatibility."""

    def test_default_risk_level_is_medium(self):
        ctx = PolicyContext()
        assert ctx.risk_level == "medium"

    def test_default_dependency_states_empty(self):
        ctx = PolicyContext()
        assert ctx.dependency_states == []

    def test_default_retryability(self):
        ctx = PolicyContext()
        assert ctx.retryability["mission_retryable"] is True
        assert ctx.retryability["max_stage_retries"] == 3

    def test_default_interactive_capability(self):
        ctx = PolicyContext()
        assert ctx.interactive_capability["ui_available"] is True
        assert ctx.interactive_capability["tools_available"] is True

    def test_default_tenant_limits(self):
        ctx = PolicyContext()
        assert ctx.tenant_limits["max_stages"] == 15
        assert ctx.tenant_limits["max_tool_calls_per_stage"] == 20
        assert ctx.tenant_limits["max_rework_cycles"] == 3


class TestPolicyContextSerialization:
    """B-013: PolicyContext round-trip serialization."""

    def test_to_dict_has_all_fields(self):
        ctx = PolicyContext()
        d = ctx.to_dict()
        assert "dependencyStates" in d
        assert "riskLevel" in d
        assert "sourceFreshness" in d
        assert "retryability" in d
        assert "interactiveCapability" in d
        assert "tenantLimits" in d
        assert "timeoutConfig" in d
        # B-013 Sprint 53 new fields
        assert "caller" in d
        assert "resourceTags" in d
        assert "environment" in d
        assert "evaluatedAt" in d

    def test_round_trip(self):
        original = PolicyContext(
            risk_level="high",
            dependency_states=[DependencyState(name="wmcp", status="degraded")],
            source_freshness={"mission_age_seconds": 42.0},
        )
        d = original.to_dict()
        restored = PolicyContext.from_dict(d)
        assert restored.risk_level == "high"
        assert len(restored.dependency_states) == 1
        assert restored.dependency_states[0].name == "wmcp"
        assert restored.dependency_states[0].status == "degraded"
        assert restored.source_freshness["mission_age_seconds"] == 42.0

    def test_from_dict_with_empty_data(self):
        ctx = PolicyContext.from_dict({})
        assert ctx.risk_level == "medium"
        assert ctx.dependency_states == []


class TestDependencyState:
    """B-013: DependencyState tracking."""

    def test_reachable_by_default(self):
        ds = DependencyState(name="wmcp")
        assert ds.status == "reachable"
        assert ds.error is None

    def test_unreachable_with_error(self):
        ds = DependencyState(name="wmcp", status="unreachable",
                             error="Connection refused")
        assert ds.status == "unreachable"
        assert "refused" in ds.error

    def test_to_dict(self):
        ds = DependencyState(name="wmcp", status="degraded",
                             last_checked=1000.0)
        d = ds.to_dict()
        assert d["name"] == "wmcp"
        assert d["status"] == "degraded"
        assert d["lastChecked"] == 1000.0


class TestCheckWmcpAvailability:
    """B-013: WMCP availability check."""

    @patch("socket.create_connection")
    def test_wmcp_reachable(self, mock_conn):
        mock_conn.return_value.__enter__ = lambda s: s
        mock_conn.return_value.__exit__ = lambda s, *a: None
        state = check_wmcp_availability()
        assert state.name == "wmcp"
        assert state.status == "reachable"
        assert state.last_checked is not None

    @patch("socket.create_connection",
           side_effect=OSError("Connection refused"))
    def test_wmcp_unreachable(self, mock_conn):
        state = check_wmcp_availability()
        assert state.name == "wmcp"
        assert state.status == "unreachable"
        assert "refused" in state.error


class TestBuildPolicyContext:
    """B-013: Full policy context builder."""

    @patch("mission.policy_context.check_wmcp_availability")
    def test_builds_from_mission(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(
            name="wmcp", status="reachable", last_checked=time.time())
        mission = {
            "risk_level": "high",
            "stages": [
                {"status": "completed"},
                {"status": "running"},
            ],
            "timeoutConfig": {},
        }
        ctx = build_policy_context(mission, time.time() - 10)
        assert ctx.risk_level == "high"
        assert len(ctx.dependency_states) == 1
        assert ctx.dependency_states[0].status == "reachable"
        assert ctx.source_freshness["mission_age_seconds"] >= 10
        assert ctx.retryability["failed_stages"] == 0
        assert ctx.interactive_capability["tools_available"] is True

    @patch("mission.policy_context.check_wmcp_availability")
    def test_wmcp_unreachable_affects_tools(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(
            name="wmcp", status="unreachable", error="down")
        mission = {"risk_level": "low", "stages": [], "timeoutConfig": {}}
        ctx = build_policy_context(mission, time.time())
        assert ctx.interactive_capability["tools_available"] is False
        assert ctx.interactive_capability["wmcp_status"] == "unreachable"

    @patch("mission.policy_context.check_wmcp_availability")
    def test_failed_stages_count(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {
            "risk_level": "medium",
            "stages": [
                {"status": "failed"},
                {"status": "failed"},
                {"status": "failed"},
            ],
            "timeoutConfig": {},
        }
        ctx = build_policy_context(mission, time.time())
        assert ctx.retryability["failed_stages"] == 3
        assert ctx.retryability["mission_retryable"] is False

    @patch("mission.policy_context.check_wmcp_availability")
    def test_default_risk_when_none(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {"risk_level": None, "stages": [], "timeoutConfig": {}}
        ctx = build_policy_context(mission, time.time())
        assert ctx.risk_level == "medium"


# --- B-014: Timeout tests ---


class TestTimeoutConfig:
    """B-014: Timeout hierarchy configuration."""

    def test_defaults(self):
        tc = TimeoutConfig()
        assert tc.mission_seconds == DEFAULT_MISSION_TIMEOUT  # 3600
        assert tc.stage_seconds == DEFAULT_STAGE_TIMEOUT      # 600
        assert tc.tool_seconds == DEFAULT_TOOL_TIMEOUT        # 120

    def test_effective_stage_timeout_default(self):
        tc = TimeoutConfig(mission_seconds=3600, stage_seconds=600)
        assert tc.effective_stage_timeout() == 600

    def test_effective_stage_timeout_with_override(self):
        tc = TimeoutConfig(mission_seconds=3600, stage_seconds=600)
        assert tc.effective_stage_timeout(300) == 300

    def test_effective_stage_timeout_capped_by_mission(self):
        tc = TimeoutConfig(mission_seconds=100, stage_seconds=600)
        # Stage timeout cannot exceed mission timeout
        assert tc.effective_stage_timeout() == 100

    def test_effective_stage_override_capped_by_mission(self):
        tc = TimeoutConfig(mission_seconds=50, stage_seconds=600)
        assert tc.effective_stage_timeout(200) == 50

    def test_round_trip(self):
        original = TimeoutConfig(mission_seconds=1800, stage_seconds=300,
                                 tool_seconds=60)
        d = original.to_dict()
        restored = TimeoutConfig.from_dict(d)
        assert restored.mission_seconds == 1800
        assert restored.stage_seconds == 300
        assert restored.tool_seconds == 60

    def test_from_dict_with_defaults(self):
        tc = TimeoutConfig.from_dict({})
        assert tc.mission_seconds == DEFAULT_MISSION_TIMEOUT
        assert tc.stage_seconds == DEFAULT_STAGE_TIMEOUT
        assert tc.tool_seconds == DEFAULT_TOOL_TIMEOUT


class TestTimedOutState:
    """B-014: TIMED_OUT state in mission state machine."""

    def test_timed_out_enum_exists(self):
        assert MissionStatus.TIMED_OUT.value == "timed_out"

    def test_running_to_timed_out_valid(self):
        assert MissionStatus.TIMED_OUT in VALID_TRANSITIONS[MissionStatus.RUNNING]

    def test_timed_out_can_retry(self):
        allowed = VALID_TRANSITIONS[MissionStatus.TIMED_OUT]
        assert MissionStatus.PLANNING in allowed
        assert MissionStatus.READY in allowed

    def test_timed_out_cannot_go_to_completed(self):
        allowed = VALID_TRANSITIONS[MissionStatus.TIMED_OUT]
        assert MissionStatus.COMPLETED not in allowed

    def test_state_transition_to_timed_out(self):
        state = MissionState(mission_id="test-1")
        state.transition_to(MissionStatus.PLANNING, "start")
        state.transition_to(MissionStatus.READY, "planned")
        state.transition_to(MissionStatus.RUNNING, "executing")
        ok = state.transition_to(MissionStatus.TIMED_OUT, "timeout")
        assert ok is True
        assert state.status == MissionStatus.TIMED_OUT

    def test_timed_out_in_to_dict(self):
        state = MissionState(mission_id="test-2")
        state.transition_to(MissionStatus.PLANNING, "start")
        state.transition_to(MissionStatus.READY, "planned")
        state.transition_to(MissionStatus.RUNNING, "exec")
        state.transition_to(MissionStatus.TIMED_OUT, "timeout")
        d = state.to_dict()
        assert d["status"] == "timed_out"

    def test_from_dict_timed_out(self):
        state = MissionState.from_dict({
            "missionId": "test-3",
            "status": "timed_out",
        })
        assert state.status == MissionStatus.TIMED_OUT


# --- B-013 Sprint 53: Caller identity tests ---


class TestCallerIdentity:
    """B-013 Sprint 53: CallerIdentity dataclass."""

    def test_defaults(self):
        ci = CallerIdentity()
        assert ci.caller_id == "anonymous"
        assert ci.caller_role == "operator"
        assert ci.source == "unknown"

    def test_custom_values(self):
        ci = CallerIdentity(caller_id="user-123", caller_role="admin",
                            source="dashboard")
        assert ci.caller_id == "user-123"
        assert ci.caller_role == "admin"
        assert ci.source == "dashboard"

    def test_to_dict(self):
        ci = CallerIdentity(caller_id="u1", caller_role="op", source="telegram")
        d = ci.to_dict()
        assert d["callerId"] == "u1"
        assert d["callerRole"] == "op"
        assert d["source"] == "telegram"

    def test_round_trip(self):
        original = CallerIdentity(caller_id="x", caller_role="scheduler",
                                  source="api")
        d = original.to_dict()
        restored = CallerIdentity.from_dict(d)
        assert restored.caller_id == "x"
        assert restored.caller_role == "scheduler"
        assert restored.source == "api"

    def test_from_dict_defaults(self):
        ci = CallerIdentity.from_dict({})
        assert ci.caller_id == "anonymous"
        assert ci.caller_role == "operator"


# --- B-013 Sprint 53: Enriched PolicyContext tests ---


class TestEnrichedPolicyContext:
    """B-013 Sprint 53: New fields in PolicyContext."""

    def test_default_caller(self):
        ctx = PolicyContext()
        assert ctx.caller.caller_id == "anonymous"

    def test_default_resource_tags_empty(self):
        ctx = PolicyContext()
        assert ctx.resource_tags == {}

    def test_default_environment(self):
        ctx = PolicyContext()
        assert ctx.environment == "production"

    def test_to_dict_includes_new_fields(self):
        ctx = PolicyContext(
            caller=CallerIdentity(caller_id="user-1", source="dashboard"),
            resource_tags={"team": "platform", "priority": "high"},
            environment="development",
            evaluated_at="2026-04-04T10:00:00Z",
        )
        d = ctx.to_dict()
        assert d["caller"]["callerId"] == "user-1"
        assert d["caller"]["source"] == "dashboard"
        assert d["resourceTags"]["team"] == "platform"
        assert d["environment"] == "development"
        assert d["evaluatedAt"] == "2026-04-04T10:00:00Z"

    def test_round_trip_with_new_fields(self):
        original = PolicyContext(
            caller=CallerIdentity(caller_id="u2", caller_role="admin",
                                  source="api"),
            resource_tags={"env": "staging"},
            environment="staging",
            evaluated_at="2026-04-04T12:00:00Z",
        )
        d = original.to_dict()
        restored = PolicyContext.from_dict(d)
        assert restored.caller.caller_id == "u2"
        assert restored.caller.source == "api"
        assert restored.resource_tags["env"] == "staging"
        assert restored.environment == "staging"
        assert restored.evaluated_at == "2026-04-04T12:00:00Z"

    def test_backward_compat_from_dict_without_new_fields(self):
        """Old data without new fields still deserializes correctly."""
        old_data = {
            "riskLevel": "high",
            "dependencyStates": [],
            "sourceFreshness": {},
        }
        ctx = PolicyContext.from_dict(old_data)
        assert ctx.risk_level == "high"
        assert ctx.caller.caller_id == "anonymous"
        assert ctx.resource_tags == {}
        assert ctx.environment == "production"


class TestDetectEnvironment:
    """B-013 Sprint 53: Environment detection."""

    @patch.dict("os.environ", {"VEZIR_ENV": "staging"}, clear=False)
    def test_vezir_env_staging(self):
        assert _detect_environment() == "staging"

    @patch.dict("os.environ", {"VEZIR_ENV": "development"}, clear=False)
    def test_vezir_env_development(self):
        assert _detect_environment() == "development"

    @patch.dict("os.environ", {"VEZIR_DEV": "1", "VEZIR_ENV": ""}, clear=False)
    def test_vezir_dev_flag(self):
        assert _detect_environment() == "development"

    @patch.dict("os.environ", {"CI": "true", "VEZIR_ENV": "", "VEZIR_DEV": ""}, clear=False)
    def test_ci_env(self):
        assert _detect_environment() == "test"

    @patch.dict("os.environ", {"VEZIR_ENV": "", "VEZIR_DEV": "", "CI": ""}, clear=False)
    def test_default_production(self):
        assert _detect_environment() == "production"


class TestBuildPolicyContextEnriched:
    """B-013 Sprint 53: build_policy_context populates new fields."""

    @patch("mission.policy_context.check_wmcp_availability")
    def test_caller_from_mission_userid(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {
            "risk_level": "medium",
            "stages": [],
            "timeoutConfig": {},
            "userId": "dashboard-user",
            "createdFrom": "dashboard",
        }
        ctx = build_policy_context(mission, time.time())
        assert ctx.caller.caller_id == "dashboard-user"
        assert ctx.caller.source == "dashboard"

    @patch("mission.policy_context.check_wmcp_availability")
    def test_resource_tags_from_mission(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {
            "risk_level": "low",
            "stages": [],
            "timeoutConfig": {},
            "resourceTags": {"team": "ops", "sprint": "53"},
        }
        ctx = build_policy_context(mission, time.time())
        assert ctx.resource_tags["team"] == "ops"
        assert ctx.resource_tags["sprint"] == "53"

    @patch("mission.policy_context.check_wmcp_availability")
    def test_evaluated_at_set(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {"risk_level": "medium", "stages": [], "timeoutConfig": {}}
        ctx = build_policy_context(mission, time.time())
        assert ctx.evaluated_at != ""
        assert "T" in ctx.evaluated_at  # ISO format

    @patch("mission.policy_context.check_wmcp_availability")
    def test_missing_userid_defaults_anonymous(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {"risk_level": "low", "stages": [], "timeoutConfig": {}}
        ctx = build_policy_context(mission, time.time())
        assert ctx.caller.caller_id == "anonymous"

    @patch("mission.policy_context.check_wmcp_availability")
    def test_empty_resource_tags(self, mock_wmcp):
        mock_wmcp.return_value = DependencyState(name="wmcp", status="reachable")
        mission = {"risk_level": "low", "stages": [], "timeoutConfig": {}}
        ctx = build_policy_context(mission, time.time())
        assert ctx.resource_tags == {}
