"""Provider selection telemetry — emit events for every routing decision (D-148)."""
from context.policy_telemetry import emit_policy_event
from providers.routing_policy import RoutingDecision


def emit_provider_selection(
    decision: RoutingDecision,
    task_type: str | None = None,
    mission_id: str | None = None,
) -> None:
    """Emit a provider_selection or provider_fallback telemetry event.

    Called on every agent call. Fields:
    - selected_provider: which agent was chosen
    - reason: why it was chosen
    - fallback_used: bool
    - fallback_reason: why fallback was triggered (if applicable)
    - task_type: review/analysis/implementation/etc.
    - mission_id: optional mission context
    """
    event_type = "provider_fallback" if decision.fallback_used else "provider_selection"
    details = {
        "selected_provider": decision.selected_provider,
        "reason": decision.reason,
        "fallback_used": decision.fallback_used,
    }
    if decision.fallback_reason:
        details["fallback_reason"] = decision.fallback_reason
    if task_type:
        details["task_type"] = task_type
    if mission_id:
        details["mission_id"] = mission_id

    emit_policy_event(event_type, details)
