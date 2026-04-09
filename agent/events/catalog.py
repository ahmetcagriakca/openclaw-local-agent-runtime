"""Event Catalog — D-102 event type definitions.

31 event types across 8 namespaces. Each event type has a fixed
string identifier used for handler registration and history queries.
"""


class EventType:
    """Event type constants. Use these instead of raw strings."""

    # ── Mission lifecycle ────────────────────────────────────────
    MISSION_STARTED = "mission.started"
    MISSION_COMPLETED = "mission.completed"
    MISSION_FAILED = "mission.failed"
    MISSION_ABORTED = "mission.aborted"

    # ── Stage lifecycle ──────────────────────────────────────────
    STAGE_ENTERING = "stage.entering"         # before context assembly
    STAGE_CONTEXT_READY = "stage.context_ready"  # context assembled, pre-LLM
    STAGE_COMPLETED = "stage.completed"
    STAGE_FAILED = "stage.failed"
    STAGE_REWORK = "stage.rework"

    # ── Tool execution ───────────────────────────────────────────
    TOOL_REQUESTED = "tool.requested"         # before permission check
    TOOL_CLEARED = "tool.cleared"             # permission OK, ready to execute
    TOOL_EXECUTED = "tool.executed"            # after MCP call returns
    TOOL_BLOCKED = "tool.blocked"             # permission denied
    TOOL_TRUNCATED = "tool.truncated"         # response auto-truncated

    # ── LLM execution ───────────────────────────────────────────
    LLM_REQUESTED = "llm.requested"           # before LLM call
    LLM_COMPLETED = "llm.completed"           # LLM response received
    LLM_FAILED = "llm.failed"

    # ── Budget ───────────────────────────────────────────────────
    BUDGET_WARNING = "budget.warning"         # approaching limit
    BUDGET_EXCEEDED = "budget.exceeded"       # hard limit hit
    BUDGET_TRUNCATED = "budget.truncated"     # response auto-truncated

    # ── Approval ─────────────────────────────────────────────────
    APPROVAL_REQUESTED = "approval.requested"
    APPROVAL_GRANTED = "approval.granted"
    APPROVAL_DENIED = "approval.denied"
    APPROVAL_TIMEOUT = "approval.timeout"

    # ── Project lifecycle (D-144) ──────────────────────────────
    PROJECT_CREATED = "project.created"
    PROJECT_STATUS_CHANGED = "project.status_changed"
    PROJECT_MISSION_LINKED = "project.mission_linked"
    PROJECT_MISSION_UNLINKED = "project.mission_unlinked"
    PROJECT_DELETED = "project.deleted"

    # ── Project workspace/artifacts (D-145) ─────────────────────
    PROJECT_WORKSPACE_ENABLED = "project.workspace_enabled"
    PROJECT_ARTIFACT_PUBLISHED = "project.artifact_published"
    PROJECT_ARTIFACT_UNPUBLISHED = "project.artifact_unpublished"

    # ── Project GitHub surface (D-151) ───────────────────────────
    PROJECT_GITHUB_BOUND = "project.github_bound"
    PROJECT_GITHUB_SYNCED = "project.github_synced"
    PROJECT_GITHUB_COMMENT_PUBLISHED = "project.github_comment_published"

    # ── Project SSE (D-145 Faz 2B) ───────────────────────────────
    PROJECT_ROLLUP_UPDATED = "project.rollup_updated"

    # ── Quality gates ────────────────────────────────────────────
    GATE_CHECKED = "gate.checked"
    GATE_PASSED = "gate.passed"
    GATE_FAILED = "gate.failed"
    GATE_REWORK = "gate.rework"

    @classmethod
    def all_types(cls) -> list[str]:
        """Return all 31 event type strings."""
        return [
            v for k, v in vars(cls).items()
            if isinstance(v, str) and not k.startswith("_")
        ]

    @classmethod
    def namespace(cls, ns: str) -> list[str]:
        """Return event types for a namespace (e.g., 'tool', 'mission')."""
        prefix = ns + "."
        return [t for t in cls.all_types() if t.startswith(prefix)]
