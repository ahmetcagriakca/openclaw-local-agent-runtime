"""Capability registry — maps task types (role + skill) to required provider capabilities (D-150)."""

from __future__ import annotations

# Canonical capability names (must match ProviderRoutingPolicy.capability_manifest keys)
TEXT_GENERATION = "text_generation"
FUNCTION_CALLING = "function_calling"
CODE_INTERPRETER = "code_interpreter"
REASONING = "reasoning"
LONG_CONTEXT = "long_context"

# Role → required capabilities mapping.
# Unknown roles get empty list (= existing Azure-first behavior per D-150 R3).
_ROLE_CAPABILITIES: dict[str, list[str]] = {
    "product-owner": [TEXT_GENERATION],
    "analyst": [TEXT_GENERATION, LONG_CONTEXT],
    "architect": [TEXT_GENERATION, REASONING, LONG_CONTEXT],
    "project-manager": [TEXT_GENERATION],
    "developer": [TEXT_GENERATION, FUNCTION_CALLING],
    "tester": [TEXT_GENERATION, FUNCTION_CALLING],
    "reviewer": [TEXT_GENERATION, REASONING],
    "security": [TEXT_GENERATION, REASONING],
    "manager": [TEXT_GENERATION],
    # Synthetic roles used by controller
    "planner": [TEXT_GENERATION, REASONING],
    "summary": [TEXT_GENERATION],
}

# Skill → additional capability overrides.
# If a skill needs capabilities beyond its role's defaults, add here.
_SKILL_CAPABILITY_OVERRIDES: dict[str, list[str]] = {
    "controlled_execution": [TEXT_GENERATION, FUNCTION_CALLING],
    "repository_discovery": [TEXT_GENERATION, LONG_CONTEXT],
    "architecture_synthesis": [TEXT_GENERATION, REASONING, LONG_CONTEXT],
    "recovery_triage": [TEXT_GENERATION, REASONING],
}


def resolve_capabilities(role: str, skill: str | None = None) -> list[str]:
    """Resolve required capabilities for a role + optional skill combination.

    D-150 R1: Every _select_agent_for_role() call resolves capabilities before routing.
    D-150 R3: Unknown role/skill pairs get empty capabilities (= Azure-first fallback).

    Args:
        role: Canonical role name (e.g., "analyst", "developer").
        skill: Optional skill name (e.g., "repository_discovery").

    Returns:
        Deduplicated list of required capability strings.
    """
    caps: set[str] = set()

    # Role-based capabilities
    role_caps = _ROLE_CAPABILITIES.get(role, [])
    caps.update(role_caps)

    # Skill overrides (union, not replace)
    if skill:
        skill_caps = _SKILL_CAPABILITY_OVERRIDES.get(skill, [])
        caps.update(skill_caps)

    return sorted(caps)


def get_role_capabilities() -> dict[str, list[str]]:
    """Return a copy of the role capabilities mapping (for telemetry/debug)."""
    return dict(_ROLE_CAPABILITIES)


def get_skill_overrides() -> dict[str, list[str]]:
    """Return a copy of the skill capability overrides (for telemetry/debug)."""
    return dict(_SKILL_CAPABILITY_OVERRIDES)
