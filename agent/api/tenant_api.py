"""Multi-tenant API — B-116.

CRUD + quota check endpoints for tenant management.
"""
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from auth.tenant import (
    TenantError,
    TenantStore,
    get_tenant_context,
)

router = APIRouter(tags=["tenants"])

_store: TenantStore | None = None


def _get_store() -> TenantStore:
    global _store
    if _store is None:
        _store = TenantStore()
    return _store


class TenantCreateRequest(BaseModel):
    tenant_id: str = Field(..., min_length=1, max_length=64, pattern="^[a-z0-9_-]+$")
    name: str = Field(..., min_length=1, max_length=256)
    settings: dict = Field(default_factory=dict)
    quota: dict = Field(default_factory=dict)


class TenantUpdateRequest(BaseModel):
    name: str | None = None
    enabled: bool | None = None
    settings: dict | None = None
    quota: dict | None = None


class QuotaCheckRequest(BaseModel):
    metric: str = Field(..., min_length=1)
    current_value: int = Field(..., ge=0)


@router.post("/tenants")
async def create_tenant(req: TenantCreateRequest):
    """Create a new tenant."""
    store = _get_store()
    try:
        tenant = store.create(
            tenant_id=req.tenant_id,
            name=req.name,
            settings=req.settings,
            quota=req.quota,
        )
        return {"status": "created", "tenant": tenant.to_dict()}
    except TenantError as e:
        raise HTTPException(status_code=409, detail=str(e))


@router.get("/tenants")
async def list_tenants(enabled_only: bool = False):
    """List all tenants."""
    store = _get_store()
    tenants = store.list(enabled_only=enabled_only)
    return {"tenants": tenants, "total": len(tenants)}


@router.get("/tenants/current")
async def get_current_tenant(request: Request):
    """Get the current tenant context from request."""
    ctx = get_tenant_context()
    store = _get_store()
    tenant = store.get(ctx.tenant_id)
    return {
        "context": ctx.to_dict(),
        "tenant": tenant.to_dict() if tenant else None,
    }


@router.get("/tenants/{tenant_id}")
async def get_tenant(tenant_id: str):
    """Get a single tenant."""
    store = _get_store()
    tenant = store.get(tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return tenant.to_dict()


@router.patch("/tenants/{tenant_id}")
async def update_tenant(tenant_id: str, req: TenantUpdateRequest):
    """Update a tenant."""
    store = _get_store()
    tenant = store.update(
        tenant_id=tenant_id,
        name=req.name,
        enabled=req.enabled,
        settings=req.settings,
        quota=req.quota,
    )
    if not tenant:
        raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
    return {"status": "updated", "tenant": tenant.to_dict()}


@router.delete("/tenants/{tenant_id}")
async def delete_tenant(tenant_id: str):
    """Delete a tenant."""
    store = _get_store()
    try:
        deleted = store.delete(tenant_id)
        if not deleted:
            raise HTTPException(status_code=404, detail=f"Tenant {tenant_id} not found")
        return {"status": "deleted", "tenant_id": tenant_id}
    except TenantError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/tenants/{tenant_id}/quota-check")
async def check_quota(tenant_id: str, req: QuotaCheckRequest):
    """Check tenant quota for a given metric."""
    store = _get_store()
    result = store.check_quota(
        tenant_id=tenant_id,
        metric=req.metric,
        current_value=req.current_value,
    )
    return result
