"""Policy API — policy management endpoints.

B-107 Sprint 49: GET list, GET detail, POST reload.
Sprint 50: POST create, PUT update, DELETE remove + mutation audit.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from pydantic import ValidationError

from mission.policy_engine import PolicyEngine

router = APIRouter(tags=["policies"])
logger = logging.getLogger("mcc.api.policy")

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


@router.post("/policies", status_code=201)
def create_policy(body: dict):
    """Create a new policy rule."""
    try:
        rule = _engine.create_rule(body)
    except (ValidationError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))

    _audit("create", rule.name)
    return {
        "name": rule.name,
        "priority": rule.priority,
        "decision": rule.decision.value,
        "created": True,
    }


@router.put("/policies/{name}")
def update_policy(name: str, body: dict):
    """Update an existing policy rule."""
    try:
        rule = _engine.update_rule(name, body)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except (ValidationError, TypeError) as e:
        raise HTTPException(status_code=422, detail=str(e))

    _audit("update", rule.name)
    return {
        "name": rule.name,
        "priority": rule.priority,
        "decision": rule.decision.value,
        "updated": True,
    }


@router.delete("/policies/{name}")
def delete_policy(name: str):
    """Delete a policy rule."""
    try:
        _engine.delete_rule(name)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))

    _audit("delete", name)
    return {"name": name, "deleted": True}


def _audit(action: str, rule_name: str) -> None:
    """Emit structured audit log for policy mutations."""
    logger.info(
        "POLICY_MUTATION action=%s rule=%s ts=%s",
        action, rule_name,
        datetime.now(timezone.utc).isoformat(),
    )
