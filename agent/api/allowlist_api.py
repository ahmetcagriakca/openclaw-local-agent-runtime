"""Allowlist API — B-009.

CRUD endpoints for multi-source allowlist management.
"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from auth.middleware import require_operator
from services.allowlist_store import AllowlistStore

logger = logging.getLogger("mcc.api.allowlist")
router = APIRouter(tags=["allowlist"])

_store = AllowlistStore()


class AllowlistCreateRequest(BaseModel):
    name: str
    source_type: str = "caller_source"
    values: list[str] = []
    description: str = ""
    enabled: bool = True


class AllowlistUpdateRequest(BaseModel):
    source_type: Optional[str] = None
    values: Optional[list[str]] = None
    description: Optional[str] = None
    enabled: Optional[bool] = None


class AllowlistCheckRequest(BaseModel):
    source_type: str
    value: str


@router.get("/allowlists")
def list_allowlists():
    """List all allowlist entries."""
    return {"allowlists": _store.to_dict(), "count": len(_store.entries)}


@router.get("/allowlists/{name}")
def get_allowlist(name: str):
    """Get a specific allowlist entry."""
    entry = _store.get(name)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Allowlist '{name}' not found")
    from dataclasses import asdict
    return asdict(entry)


@router.post("/allowlists", status_code=201)
def create_allowlist(req: AllowlistCreateRequest, _operator=Depends(require_operator)):
    """Create a new allowlist entry."""
    try:
        entry = _store.create(req.model_dump())
        from dataclasses import asdict
        return asdict(entry)
    except ValueError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.put("/allowlists/{name}")
def update_allowlist(name: str, req: AllowlistUpdateRequest, _operator=Depends(require_operator)):
    """Update an existing allowlist entry."""
    try:
        data = {k: v for k, v in req.model_dump().items() if v is not None}
        entry = _store.update(name, data)
        from dataclasses import asdict
        return asdict(entry)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/allowlists/{name}")
def delete_allowlist(name: str, _operator=Depends(require_operator)):
    """Delete an allowlist entry."""
    try:
        _store.delete(name)
        return {"deleted": name}
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/allowlists/check")
def check_allowlist(req: AllowlistCheckRequest):
    """Check if a value is allowed."""
    allowed = _store.check(req.source_type, req.value)
    return {"allowed": allowed, "source_type": req.source_type, "value": req.value}


@router.post("/allowlists/reload")
def reload_allowlists(_operator=Depends(require_operator)):
    """Reload allowlists from YAML files."""
    count = _store.load()
    return {"reloaded": count}
