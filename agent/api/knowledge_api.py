"""Knowledge/connector API — B-114.

CRUD + search + mission-context endpoints for knowledge entries.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from auth.middleware import require_operator
from services.knowledge_store import KnowledgeStore

router = APIRouter(tags=["knowledge"])

_store: KnowledgeStore | None = None


def _get_store() -> KnowledgeStore:
    global _store
    if _store is None:
        _store = KnowledgeStore()
    return _store


class KnowledgeCreateRequest(BaseModel):
    name: str = Field(..., min_length=1, max_length=256)
    connector_type: str = Field(..., pattern="^(file|url|text)$")
    content: str = Field(..., min_length=1)
    metadata: dict = Field(default_factory=dict)
    tags: list[str] = Field(default_factory=list)


class KnowledgeUpdateRequest(BaseModel):
    name: str | None = None
    content: str | None = None
    metadata: dict | None = None
    tags: list[str] | None = None
    enabled: bool | None = None


class MissionKnowledgeRequest(BaseModel):
    mission_tags: list[str] = Field(default_factory=list)
    entry_ids: list[str] = Field(default_factory=list)


@router.post("/knowledge")
async def create_knowledge(req: KnowledgeCreateRequest, _operator=Depends(require_operator)):
    """Create a new knowledge entry."""
    store = _get_store()
    entry = store.add(
        name=req.name,
        connector_type=req.connector_type,
        content=req.content,
        metadata=req.metadata,
        tags=req.tags,
    )
    from dataclasses import asdict
    return {"status": "created", "entry": asdict(entry)}


@router.get("/knowledge")
async def list_knowledge(
    connector_type: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    enabled_only: bool = True,
    limit: int = 50,
    offset: int = 0,
):
    """List knowledge entries with filters."""
    store = _get_store()
    entries, total = store.list(
        connector_type=connector_type,
        tag=tag,
        search=search,
        enabled_only=enabled_only,
        limit=limit,
        offset=offset,
    )
    return {"entries": entries, "total": total}


@router.get("/knowledge/stats")
async def knowledge_stats():
    """Get knowledge store statistics."""
    store = _get_store()
    return store.stats()


@router.get("/knowledge/{entry_id}")
async def get_knowledge(entry_id: str):
    """Get a single knowledge entry."""
    store = _get_store()
    entry = store.get(entry_id)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Knowledge entry {entry_id} not found")
    from dataclasses import asdict
    return asdict(entry)


@router.patch("/knowledge/{entry_id}")
async def update_knowledge(entry_id: str, req: KnowledgeUpdateRequest, _operator=Depends(require_operator)):
    """Update a knowledge entry."""
    store = _get_store()
    entry = store.update(
        entry_id=entry_id,
        name=req.name,
        content=req.content,
        metadata=req.metadata,
        tags=req.tags,
        enabled=req.enabled,
    )
    if not entry:
        raise HTTPException(status_code=404, detail=f"Knowledge entry {entry_id} not found")
    from dataclasses import asdict
    return {"status": "updated", "entry": asdict(entry)}


@router.delete("/knowledge/{entry_id}")
async def delete_knowledge(entry_id: str, _operator=Depends(require_operator)):
    """Delete a knowledge entry."""
    store = _get_store()
    deleted = store.delete(entry_id)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Knowledge entry {entry_id} not found")
    return {"status": "deleted", "entry_id": entry_id}


@router.post("/knowledge/mission-context")
async def get_mission_knowledge(req: MissionKnowledgeRequest):
    """Get knowledge entries relevant to a mission context.

    Selects by explicit entry IDs or by tag matching.
    Used by ContextAssembler for mission enrichment.
    """
    store = _get_store()
    entries = store.get_for_mission(
        mission_tags=req.mission_tags,
        entry_ids=req.entry_ids,
    )
    return {"entries": entries, "count": len(entries)}
