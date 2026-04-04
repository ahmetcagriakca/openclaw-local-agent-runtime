"""Policy context builder for pre-stage evaluation.

B-013: Richer policyContext — provides dependency state, risk level,
source freshness, retryability, interactive capability, tenant limits,
caller identity, resource tags, and environment metadata to the policy
evaluation pipeline.

B-014: Timeout configuration — mission/stage/tool timeout hierarchy.
"""
import os
import time
from dataclasses import dataclass, field
from typing import Optional

# B-014: Default timeout values (seconds)
DEFAULT_MISSION_TIMEOUT = 3600  # 1 hour
DEFAULT_STAGE_TIMEOUT = 600     # 10 minutes
DEFAULT_TOOL_TIMEOUT = 120      # 2 minutes


@dataclass
class TimeoutConfig:
    """B-014: Timeout hierarchy — mission > stage > tool."""
    mission_seconds: int = DEFAULT_MISSION_TIMEOUT
    stage_seconds: int = DEFAULT_STAGE_TIMEOUT
    tool_seconds: int = DEFAULT_TOOL_TIMEOUT

    def effective_stage_timeout(self, stage_override: Optional[int] = None) -> int:
        """Return the effective stage timeout, respecting hierarchy."""
        timeout = stage_override if stage_override is not None else self.stage_seconds
        # Stage timeout cannot exceed remaining mission timeout
        return min(timeout, self.mission_seconds)

    def to_dict(self) -> dict:
        return {
            "missionSeconds": self.mission_seconds,
            "stageSeconds": self.stage_seconds,
            "toolSeconds": self.tool_seconds,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "TimeoutConfig":
        return cls(
            mission_seconds=data.get("missionSeconds", DEFAULT_MISSION_TIMEOUT),
            stage_seconds=data.get("stageSeconds", DEFAULT_STAGE_TIMEOUT),
            tool_seconds=data.get("toolSeconds", DEFAULT_TOOL_TIMEOUT),
        )


@dataclass
class DependencyState:
    """Per-dependency availability tracking."""
    name: str
    status: str = "reachable"  # reachable | degraded | unreachable
    last_checked: Optional[float] = None
    error: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "status": self.status,
            "lastChecked": self.last_checked,
            "error": self.error,
        }


@dataclass
class CallerIdentity:
    """B-013 Sprint 53: Caller identity for policy evaluation."""
    caller_id: str = "anonymous"
    caller_role: str = "operator"  # operator | dashboard | telegram | api | scheduler
    source: str = "unknown"        # dashboard | telegram | api | cli | scheduler

    def to_dict(self) -> dict:
        return {
            "callerId": self.caller_id,
            "callerRole": self.caller_role,
            "source": self.source,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "CallerIdentity":
        return cls(
            caller_id=data.get("callerId", "anonymous"),
            caller_role=data.get("callerRole", "operator"),
            source=data.get("source", "unknown"),
        )


@dataclass
class PolicyContext:
    """B-013: Rich policy context for pre-stage evaluation.

    All fields are optional with safe defaults so existing missions
    continue to work without breakage.
    """
    # Per-dependency availability (MCP reachable/degraded/unreachable)
    dependency_states: list = field(default_factory=list)

    # D-128: Risk level computed at mission creation
    risk_level: str = "medium"

    # Per-source age tracking (normalizer metadata)
    source_freshness: dict = field(default_factory=dict)

    # Mission/stage retry eligibility
    retryability: dict = field(default_factory=lambda: {
        "mission_retryable": True,
        "max_stage_retries": 3,
    })

    # Tool/UI availability state
    interactive_capability: dict = field(default_factory=lambda: {
        "ui_available": True,
        "tools_available": True,
    })

    # D-121: Guardrail thresholds
    tenant_limits: dict = field(default_factory=lambda: {
        "max_stages": 15,
        "max_tool_calls_per_stage": 20,
        "max_rework_cycles": 3,
    })

    # B-014: Timeout configuration
    timeout_config: TimeoutConfig = field(default_factory=TimeoutConfig)

    # B-013 Sprint 53: Caller identity
    caller: CallerIdentity = field(default_factory=CallerIdentity)

    # B-013 Sprint 53: Resource tags (mission-level labels)
    resource_tags: dict = field(default_factory=dict)

    # B-013 Sprint 53: Environment metadata
    environment: str = "production"  # production | development | staging | test

    # B-013 Sprint 53: Evaluation timestamp (ISO 8601)
    evaluated_at: str = ""

    def to_dict(self) -> dict:
        return {
            "dependencyStates": [d.to_dict() for d in self.dependency_states],
            "riskLevel": self.risk_level,
            "sourceFreshness": self.source_freshness,
            "retryability": self.retryability,
            "interactiveCapability": self.interactive_capability,
            "tenantLimits": self.tenant_limits,
            "timeoutConfig": self.timeout_config.to_dict(),
            "caller": self.caller.to_dict(),
            "resourceTags": self.resource_tags,
            "environment": self.environment,
            "evaluatedAt": self.evaluated_at,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PolicyContext":
        dep_states = [
            DependencyState(
                name=d["name"],
                status=d.get("status", "reachable"),
                last_checked=d.get("lastChecked"),
                error=d.get("error"),
            )
            for d in data.get("dependencyStates", [])
        ]
        timeout_data = data.get("timeoutConfig", {})
        caller_data = data.get("caller", {})
        return cls(
            dependency_states=dep_states,
            risk_level=data.get("riskLevel", "medium"),
            source_freshness=data.get("sourceFreshness", {}),
            retryability=data.get("retryability", {
                "mission_retryable": True, "max_stage_retries": 3}),
            interactive_capability=data.get("interactiveCapability", {
                "ui_available": True, "tools_available": True}),
            tenant_limits=data.get("tenantLimits", {
                "max_stages": 15, "max_tool_calls_per_stage": 20,
                "max_rework_cycles": 3}),
            timeout_config=TimeoutConfig.from_dict(timeout_data),
            caller=CallerIdentity.from_dict(caller_data),
            resource_tags=data.get("resourceTags", {}),
            environment=data.get("environment", "production"),
            evaluated_at=data.get("evaluatedAt", ""),
        )


def check_wmcp_availability() -> DependencyState:
    """Check WMCP (Windows MCP Proxy) availability on port 8001."""
    import socket
    state = DependencyState(name="wmcp", last_checked=time.time())
    try:
        with socket.create_connection(("127.0.0.1", 8001), timeout=2):
            state.status = "reachable"
    except OSError as e:
        state.status = "unreachable"
        state.error = str(e)
    return state


def _detect_environment() -> str:
    """Detect runtime environment from env vars."""
    env = os.environ.get("VEZIR_ENV", "").lower()
    if env in ("production", "development", "staging", "test"):
        return env
    if os.environ.get("VEZIR_DEV", "") == "1":
        return "development"
    if os.environ.get("CI", ""):
        return "test"
    return "production"


def build_policy_context(
    mission: dict,
    mission_start_time: float,
) -> PolicyContext:
    """Build a PolicyContext for pre-stage evaluation.

    Args:
        mission: The current mission dict (has risk_level, stages, etc.)
        mission_start_time: time.time() when mission started
    """
    from datetime import datetime, timezone as tz

    # Dependency states: check WMCP
    wmcp_state = check_wmcp_availability()
    dependency_states = [wmcp_state]

    # Risk level from mission (D-128, computed at creation)
    risk_level = mission.get("risk_level") or "medium"

    # Source freshness: mission age
    mission_age_s = time.time() - mission_start_time
    source_freshness = {
        "mission_age_seconds": round(mission_age_s, 1),
        "data_source": "file_store",
    }

    # Retryability from mission state
    stages = mission.get("stages", [])
    failed_count = sum(1 for s in stages if s.get("status") == "failed")
    retryability = {
        "mission_retryable": failed_count < 3,
        "max_stage_retries": 3,
        "failed_stages": failed_count,
    }

    # Interactive capability: WMCP determines tool availability
    tools_available = wmcp_state.status != "unreachable"
    interactive_capability = {
        "ui_available": True,
        "tools_available": tools_available,
        "wmcp_status": wmcp_state.status,
    }

    # Tenant limits (D-121 defaults)
    tenant_limits = {
        "max_stages": 15,
        "max_tool_calls_per_stage": 20,
        "max_rework_cycles": 3,
    }

    # Timeout config from mission or defaults
    timeout_data = mission.get("timeoutConfig", {})
    timeout_config = TimeoutConfig.from_dict(timeout_data) if timeout_data else TimeoutConfig()

    # B-013 Sprint 53: Caller identity from mission metadata
    user_id = mission.get("userId") or "anonymous"
    created_from = mission.get("createdFrom") or "unknown"
    caller = CallerIdentity(
        caller_id=user_id,
        caller_role="operator",
        source=created_from,
    )

    # B-013 Sprint 53: Resource tags from mission
    resource_tags = mission.get("resourceTags") or {}

    # B-013 Sprint 53: Environment detection
    environment = _detect_environment()

    # B-013 Sprint 53: Evaluation timestamp
    evaluated_at = datetime.now(tz.utc).isoformat()

    return PolicyContext(
        dependency_states=dependency_states,
        risk_level=risk_level,
        source_freshness=source_freshness,
        retryability=retryability,
        interactive_capability=interactive_capability,
        tenant_limits=tenant_limits,
        timeout_config=timeout_config,
        caller=caller,
        resource_tags=resource_tags,
        environment=environment,
        evaluated_at=evaluated_at,
    )
