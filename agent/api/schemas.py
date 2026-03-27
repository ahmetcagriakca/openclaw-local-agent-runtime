"""API response schemas — D-067: FROZEN after Sprint 8 exit.

Post-freeze: additive fields only, no removal, no type change.
Versioned as /api/v1/.

GPT Review fixes applied:
- Fix 2: DataQuality enum (known_zero → fresh/partial)
- Fix 3: Response wrapper schemas (all endpoints return *Response)
- Fix 4: CapabilityStatus tri-state, ComponentHealth with name
- Fix 8: TelemetryEntry with missionId, sourceFile
"""
from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

# ── D-068: Data Quality States (GPT Fix 2) ──────────────────────

class DataQuality(str, Enum):
    """Response-level data quality indicator (D-068).

    GPT Fix 2: known_zero removed. fresh/partial added.
    Priority when multiple conditions: degraded > stale > partial > fresh.
    """
    FRESH = "fresh"              # All sources present and below threshold
    PARTIAL = "partial"          # ≥1 source present but ≥1 missing
    STALE = "stale"              # ≥1 source above stale threshold
    DEGRADED = "degraded"        # ≥1 source parse error or circuit open
    UNKNOWN = "unknown"          # All sources missing — no data
    NOT_REACHED = "not_reached"  # Source not yet created (mission not started)


class MissionState(str, Enum):
    """Mission state machine — 10 states."""
    PENDING = "pending"
    PLANNING = "planning"
    EXECUTING = "executing"
    GATE_CHECK = "gate_check"
    REWORK = "rework"
    APPROVAL_WAIT = "approval_wait"
    COMPLETED = "completed"
    FAILED = "failed"
    ABORTED = "aborted"
    TIMED_OUT = "timed_out"


# ── Source & Freshness ───────────────────────────────────────────

class SourceInfo(BaseModel):
    """Per-source freshness and status."""
    name: str
    ageMs: int = 0
    status: DataQuality = DataQuality.UNKNOWN


class ResponseMeta(BaseModel):
    """Response envelope metadata — present in every API response."""
    freshnessMs: int = 0
    dataQuality: DataQuality = DataQuality.UNKNOWN
    sourcesUsed: list[SourceInfo] = Field(default_factory=list)
    sourcesMissing: list[str] = Field(default_factory=list)
    generatedAt: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ── Gate & Findings ──────────────────────────────────────────────

class Finding(BaseModel):
    """Single gate finding."""
    check: str
    status: str  # pass | fail | warn
    detail: str = ""


class GateResultDetail(BaseModel):
    """Structured gate result per stage."""
    gateName: str
    passed: bool
    findings: list[Finding] = Field(default_factory=list)


# ── Tool Call Detail ─────────────────────────────────────────────

class ToolCallDetail(BaseModel):
    """Single tool call within a stage."""
    tool: str
    params: dict = Field(default_factory=dict)
    success: bool = True
    error: Optional[str] = None
    durationMs: int = 0
    risk: str = "unknown"
    tokenTruncated: bool = False
    tokenBlocked: bool = False


# ── Stage ────────────────────────────────────────────────────────

class StageDetail(BaseModel):
    """Single mission stage."""
    index: int = 0
    role: str = ""
    agentUsed: Optional[str] = None
    status: str = "unknown"
    error: Optional[str] = None
    result: Optional[str] = None
    systemPrompt: Optional[str] = None
    userPrompt: Optional[str] = None
    turnsUsed: int = 0
    gateResults: Optional[GateResultDetail] = None
    denyForensics: Optional[dict] = None
    isRework: bool = False
    reworkCycle: int = 0
    isRecovery: bool = False
    toolCalls: int = 0
    policyDenies: int = 0
    durationMs: Optional[int] = None
    startedAt: Optional[str] = None
    finishedAt: Optional[str] = None
    toolCallDetails: list[ToolCallDetail] = Field(default_factory=list)


# ── Mission ──────────────────────────────────────────────────────

class SignalArtifact(BaseModel):
    """Pending signal artifact (mutation request waiting for controller)."""
    requestId: str
    type: str  # approve | reject | cancel | retry
    targetId: str
    missionId: str
    requestedAt: str
    source: str = "dashboard"
    ageSeconds: int = 0


class MissionSummary(BaseModel):
    """Full mission detail."""
    missionId: str
    state: str = "unknown"
    goal: Optional[str] = None
    complexity: Optional[str] = None
    error: Optional[str] = None
    stages: list[StageDetail] = Field(default_factory=list)
    denyForensics: list[dict] = Field(default_factory=list)
    pendingSignals: list[SignalArtifact] = Field(default_factory=list)
    totalPolicyDenies: int = 0
    artifactCount: int = 0
    totalDurationMs: Optional[int] = None
    startedAt: Optional[str] = None
    completedAt: Optional[str] = None
    finalState: Optional[str] = None
    stateTransitions: list[dict] = Field(default_factory=list)


class MissionListItem(BaseModel):
    """Mission list entry."""
    missionId: str
    state: str = "unknown"
    goal: Optional[str] = None
    dataQuality: DataQuality = DataQuality.UNKNOWN
    startedAt: Optional[str] = None
    stageCount: int = 0
    currentStage: int = 0
    stageSummary: str = ""


# ── Capability (GPT Fix 4: tri-state) ───────────────────────────

class CapabilityStatus(str, Enum):
    """Tri-state capability status."""
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class CapabilityEntry(BaseModel):
    """Single capability — tri-state, not bool."""
    name: str
    status: CapabilityStatus = CapabilityStatus.UNKNOWN
    since: Optional[str] = None
    detail: Optional[str] = None


# ── Health ───────────────────────────────────────────────────────

class ComponentHealth(BaseModel):
    """Per-component health."""
    name: str
    status: str = "unknown"  # ok | degraded | error | unknown
    lastCheckAt: Optional[str] = None
    detail: Optional[str] = None


# ── Approval ─────────────────────────────────────────────────────

class ApprovalEntry(BaseModel):
    """Approval record."""
    id: str
    missionId: Optional[str] = None
    toolName: Optional[str] = None
    risk: Optional[str] = None
    status: str = "unknown"
    requestedAt: Optional[str] = None
    respondedAt: Optional[str] = None


# ── Telemetry (GPT Fix 8: missionId + sourceFile) ───────────────

class TelemetryEntry(BaseModel):
    """Single telemetry event."""
    type: str
    timestamp: Optional[str] = None
    missionId: Optional[str] = None
    sourceFile: str = ""
    data: dict[str, Any] = Field(default_factory=dict)


# ── Response Wrappers (GPT Fix 3) ───────────────────────────────

class MissionDetailResponse(BaseModel):
    """Wrapper for single mission detail."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    mission: MissionSummary


class MissionListResponse(BaseModel):
    """Wrapper for mission list."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    missions: list[MissionListItem] = Field(default_factory=list)


class StageListResponse(BaseModel):
    """Wrapper for stage list."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    stages: list[StageDetail] = Field(default_factory=list)


class HealthResponse(BaseModel):
    """System health response."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    status: str = "unknown"
    components: dict[str, ComponentHealth] = Field(default_factory=dict)


class ApprovalListResponse(BaseModel):
    """Wrapper for approval list."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    approvals: list[ApprovalEntry] = Field(default_factory=list)


class TelemetryResponse(BaseModel):
    """Wrapper for telemetry events."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    events: list[TelemetryEntry] = Field(default_factory=list)


class CapabilitiesResponse(BaseModel):
    """Wrapper for capabilities."""
    meta: ResponseMeta = Field(default_factory=ResponseMeta)
    capabilities: dict[str, CapabilityEntry] = Field(default_factory=dict)


# ── Mutation Response (D-096: Full Lifecycle) ────────────────────

class MutationResponse(BaseModel):
    """D-096 mutation response contract.

    API always returns lifecycleState=requested.
    Subsequent states (accepted/applied/rejected/timed_out) via SSE only.
    """
    requestId: str
    lifecycleState: str = "requested"
    targetId: str
    requestedAt: str
    acceptedAt: Optional[str] = None
    appliedAt: Optional[str] = None
    rejectedReason: Optional[str] = None
    timeoutAt: Optional[str] = None


# ── Error ────────────────────────────────────────────────────────

class APIError(BaseModel):
    """Standard error response."""
    error: str
    detail: Optional[str] = None
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat())
