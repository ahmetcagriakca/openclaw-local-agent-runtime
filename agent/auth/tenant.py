"""Multi-tenant isolation — B-116.

Tenant model with namespace isolation for mission and data separation.
Integrates with Session model and API middleware.
"""
from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.tenant")

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
TENANT_STORE_PATH = str(_ROOT / "config" / "tenants.json")

# Default tenant for backward compatibility
DEFAULT_TENANT_ID = "default"


@dataclass
class Tenant:
    """Tenant model for namespace isolation."""
    tenant_id: str
    name: str
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    settings: dict = field(default_factory=dict)
    quota: dict = field(default_factory=lambda: {
        "max_missions": 100,
        "max_concurrent": 5,
        "max_tokens_per_day": 1_000_000,
    })

    def to_dict(self) -> dict:
        return asdict(self)


class TenantStore:
    """JSON-backed tenant store with thread-safe CRUD.

    Manages tenant lifecycle and isolation boundaries.
    Default tenant is auto-created for backward compatibility.
    """

    def __init__(self, store_path: str = None):
        self._path = store_path or TENANT_STORE_PATH
        self._tenants: dict[str, Tenant] = {}
        self._lock = threading.Lock()
        self._load()
        self._ensure_default()

    def _load(self) -> None:
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for raw in data.get("tenants", []):
                    tenant = Tenant(**raw)
                    self._tenants[tenant.tenant_id] = tenant
                logger.info("TenantStore loaded %d tenants", len(self._tenants))
            except Exception as e:
                logger.warning("TenantStore load failed: %s", e)
                self._tenants = {}

    def _save(self) -> None:
        try:
            data = {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "tenants": [asdict(t) for t in self._tenants.values()],
            }
            atomic_write_json(self._path, data)
        except Exception as e:
            logger.error("TenantStore save failed: %s", e)

    def _ensure_default(self) -> None:
        """Ensure default tenant exists for backward compatibility."""
        if DEFAULT_TENANT_ID not in self._tenants:
            self._tenants[DEFAULT_TENANT_ID] = Tenant(
                tenant_id=DEFAULT_TENANT_ID,
                name="Default Tenant",
                settings={"is_default": True},
            )
            self._save()

    def create(self, tenant_id: str, name: str,
               settings: dict = None, quota: dict = None) -> Tenant:
        """Create a new tenant."""
        with self._lock:
            if tenant_id in self._tenants:
                raise TenantError(f"Tenant {tenant_id} already exists")

            tenant = Tenant(
                tenant_id=tenant_id,
                name=name,
                settings=settings or {},
            )
            if quota:
                tenant.quota.update(quota)

            self._tenants[tenant_id] = tenant
            self._save()

        logger.info("Tenant created: %s (%s)", tenant_id, name)
        return tenant

    def get(self, tenant_id: str) -> Optional[Tenant]:
        """Get a tenant by ID."""
        with self._lock:
            return self._tenants.get(tenant_id)

    def update(self, tenant_id: str, name: str = None,
               enabled: bool = None, settings: dict = None,
               quota: dict = None) -> Optional[Tenant]:
        """Update an existing tenant."""
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return None

            if name is not None:
                tenant.name = name
            if enabled is not None:
                tenant.enabled = enabled
            if settings is not None:
                tenant.settings.update(settings)
            if quota is not None:
                tenant.quota.update(quota)
            tenant.updated_at = datetime.now(timezone.utc).isoformat()

            self._save()
            return tenant

    def delete(self, tenant_id: str) -> bool:
        """Delete a tenant. Cannot delete default tenant."""
        if tenant_id == DEFAULT_TENANT_ID:
            raise TenantError("Cannot delete default tenant")

        with self._lock:
            if tenant_id not in self._tenants:
                return False
            del self._tenants[tenant_id]
            self._save()

        logger.info("Tenant deleted: %s", tenant_id)
        return True

    def list(self, enabled_only: bool = False) -> list[dict]:
        """List all tenants."""
        with self._lock:
            items = list(self._tenants.values())
        if enabled_only:
            items = [t for t in items if t.enabled]
        return [asdict(t) for t in items]

    def check_quota(self, tenant_id: str, metric: str, current_value: int) -> dict:
        """Check if a tenant is within quota limits.

        Returns {allowed: bool, limit: int, current: int, metric: str}.
        """
        with self._lock:
            tenant = self._tenants.get(tenant_id)
            if not tenant:
                return {"allowed": False, "reason": "tenant_not_found"}
            if not tenant.enabled:
                return {"allowed": False, "reason": "tenant_disabled"}

        limit = tenant.quota.get(metric, 0)
        if limit <= 0:
            return {"allowed": True, "limit": 0, "current": current_value, "metric": metric}

        allowed = current_value < limit
        return {
            "allowed": allowed,
            "limit": limit,
            "current": current_value,
            "metric": metric,
            "reason": None if allowed else "quota_exceeded",
        }

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._tenants)


class TenantContext:
    """Request-scoped tenant context.

    Provides tenant isolation for the current request/operation.
    Used by API middleware to set and access tenant info.
    """

    def __init__(self, tenant_id: str = DEFAULT_TENANT_ID):
        self.tenant_id = tenant_id
        self.resolved_at = datetime.now(timezone.utc).isoformat()

    def scope_mission_id(self, mission_id: str) -> str:
        """Return tenant-scoped mission identifier."""
        if self.tenant_id == DEFAULT_TENANT_ID:
            return mission_id
        return f"{self.tenant_id}:{mission_id}"

    def matches_mission(self, scoped_id: str) -> bool:
        """Check if a scoped mission ID belongs to this tenant."""
        if self.tenant_id == DEFAULT_TENANT_ID:
            return ":" not in scoped_id or scoped_id.startswith(f"{DEFAULT_TENANT_ID}:")
        return scoped_id.startswith(f"{self.tenant_id}:")

    def extract_mission_id(self, scoped_id: str) -> str:
        """Extract raw mission ID from tenant-scoped ID."""
        if ":" in scoped_id:
            parts = scoped_id.split(":", 1)
            return parts[1]
        return scoped_id

    def to_dict(self) -> dict:
        return {
            "tenant_id": self.tenant_id,
            "resolved_at": self.resolved_at,
        }


# Thread-local tenant context
_local = threading.local()


def get_tenant_context() -> TenantContext:
    """Get current tenant context (thread-local)."""
    ctx = getattr(_local, "tenant_context", None)
    if ctx is None:
        ctx = TenantContext()
        _local.tenant_context = ctx
    return ctx


def set_tenant_context(tenant_id: str) -> TenantContext:
    """Set tenant context for the current thread."""
    ctx = TenantContext(tenant_id=tenant_id)
    _local.tenant_context = ctx
    return ctx


class TenantError(Exception):
    """Tenant operation error."""
    pass
