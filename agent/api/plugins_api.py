"""Plugin lifecycle API — D-136, Sprint 59 Task 59.2/59.3.

10 endpoints: list, search, details, install, uninstall,
enable, disable, config, events, stats.
"""
from dataclasses import asdict

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from services.plugin_marketplace import PluginMarketplaceStore

router = APIRouter(tags=["plugins"])

_store: PluginMarketplaceStore | None = None


def _get_store() -> PluginMarketplaceStore:
    global _store
    if _store is None:
        _store = PluginMarketplaceStore()
        _store.discover_and_index()
    return _store


# -- Response models --

class PluginResponse(BaseModel):
    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    status: str
    capabilities: list[str] = []
    risk_tier: str = "high"
    source: str = "local"
    trust_status: str = "unknown"
    category: str = "general"
    tags: list[str] = []
    installed_at: str | None = None
    updated_at: str | None = None


class PluginListResponse(BaseModel):
    plugins: list[PluginResponse]
    total: int


class PluginStatsResponse(BaseModel):
    total: int
    available: int
    installed: int
    enabled: int
    disabled: int
    by_category: dict[str, int]
    by_risk_tier: dict[str, int]


class PluginConfigRequest(BaseModel):
    config: dict = Field(default_factory=dict)


class MessageResponse(BaseModel):
    message: str
    plugin_id: str
    status: str


# -- Read endpoints (Task 59.2) --

@router.get("/plugins", response_model=PluginListResponse)
def list_plugins():
    """List all plugins in the marketplace."""
    store = _get_store()
    entries = store.list_all()
    return PluginListResponse(
        plugins=[PluginResponse(**asdict(e)) for e in entries],
        total=len(entries),
    )


@router.get("/plugins/search", response_model=PluginListResponse)
def search_plugins(q: str = "", status: str = "", category: str = ""):
    """Search/filter plugins by query, status, or category."""
    store = _get_store()
    entries = store.filter(
        query=q or None,
        status=status or None,
        category=category or None,
    )
    return PluginListResponse(
        plugins=[PluginResponse(**asdict(e)) for e in entries],
        total=len(entries),
    )


@router.get("/plugins/events")
def plugin_events(limit: int = 50):
    """Get recent plugin marketplace events."""
    store = _get_store()
    return {"events": store.events(limit=limit)}


@router.get("/plugins/stats", response_model=PluginStatsResponse)
def plugin_stats():
    """Get plugin marketplace statistics."""
    store = _get_store()
    return PluginStatsResponse(**store.stats())


@router.get("/plugins/{plugin_id}", response_model=PluginResponse)
def get_plugin(plugin_id: str):
    """Get plugin details by ID."""
    store = _get_store()
    entry = store.get(plugin_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    return PluginResponse(**asdict(entry))


# -- Write endpoints (Task 59.3 — installer) --

@router.post("/plugins/{plugin_id}/install", response_model=MessageResponse)
def install_plugin(plugin_id: str):
    """Install a plugin from the marketplace."""
    store = _get_store()
    entry = store.get(plugin_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    if entry.status != "available":
        raise HTTPException(status_code=409, detail=f"Plugin '{plugin_id}' already installed (status={entry.status})")
    if not store.update_status(plugin_id, "installed"):
        raise HTTPException(status_code=422, detail=f"Cannot install plugin '{plugin_id}'")
    return MessageResponse(message="Plugin installed", plugin_id=plugin_id, status="installed")


@router.post("/plugins/{plugin_id}/uninstall", response_model=MessageResponse)
def uninstall_plugin(plugin_id: str):
    """Uninstall a plugin."""
    store = _get_store()
    entry = store.get(plugin_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    if entry.status == "available":
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' is not installed")
    if not store.update_status(plugin_id, "available"):
        raise HTTPException(status_code=422, detail=f"Cannot uninstall plugin '{plugin_id}'")
    return MessageResponse(message="Plugin uninstalled", plugin_id=plugin_id, status="available")


@router.post("/plugins/{plugin_id}/enable", response_model=MessageResponse)
def enable_plugin(plugin_id: str):
    """Enable an installed plugin."""
    store = _get_store()
    entry = store.get(plugin_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    if not store.update_status(plugin_id, "enabled"):
        raise HTTPException(status_code=422, detail=f"Cannot enable plugin '{plugin_id}' from status '{entry.status}'")
    return MessageResponse(message="Plugin enabled", plugin_id=plugin_id, status="enabled")


@router.post("/plugins/{plugin_id}/disable", response_model=MessageResponse)
def disable_plugin(plugin_id: str):
    """Disable a plugin."""
    store = _get_store()
    entry = store.get(plugin_id)
    if entry is None:
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    if not store.update_status(plugin_id, "disabled"):
        raise HTTPException(status_code=422, detail=f"Cannot disable plugin '{plugin_id}' from status '{entry.status}'")
    return MessageResponse(message="Plugin disabled", plugin_id=plugin_id, status="disabled")


@router.put("/plugins/{plugin_id}/config", response_model=MessageResponse)
def update_plugin_config(plugin_id: str, body: PluginConfigRequest):
    """Update plugin configuration."""
    store = _get_store()
    if not store.update_config(plugin_id, body.config):
        raise HTTPException(status_code=404, detail=f"Plugin '{plugin_id}' not found")
    entry = store.get(plugin_id)
    return MessageResponse(message="Config updated", plugin_id=plugin_id, status=entry.status)
