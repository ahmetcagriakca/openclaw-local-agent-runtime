"""Policy API — read-only policy management endpoints.

B-107 Sprint 49: GET list, GET detail, POST reload.
Write API (POST/PUT/DELETE) deferred to S50.
"""

from fastapi import APIRouter, HTTPException

from mission.policy_engine import PolicyEngine

router = APIRouter(tags=["policies"])

# Shared engine instance
_engine = PolicyEngine()


@router.get("/policies")
def list_policies():
    """List all loaded policy rules."""
    return {
        "rules": _engine.to_dict(),
        "count": len(_engine.rules),
        "errors": _engine.load_errors,
    }


@router.get("/policies/{name}")
def get_policy(name: str):
    """Get a specific policy rule by name."""
    rule = _engine.get_rule(name)
    if rule is None:
        raise HTTPException(status_code=404, detail=f"Policy rule '{name}' not found")
    return {
        "name": rule.name,
        "priority": rule.priority,
        "condition": rule.condition,
        "decision": rule.decision.value,
        "fallback": rule.fallback,
        "description": rule.description,
    }


@router.post("/policies/reload")
def reload_policies():
    """Reload all policy rules from YAML files."""
    count = _engine.load_rules()
    return {
        "reloaded": count,
        "errors": _engine.load_errors,
    }
