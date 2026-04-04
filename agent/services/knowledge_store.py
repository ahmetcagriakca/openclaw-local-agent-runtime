"""Knowledge/connector input layer — B-114.

Manages external knowledge sources (file, URL, text) for mission context
enrichment. Integrates with ContextAssembler for tier-based delivery.
"""
import hashlib
import json
import logging
import os
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.knowledge")

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
KNOWLEDGE_STORE_PATH = str(_ROOT / "config" / "knowledge-store.json")


@dataclass
class KnowledgeEntry:
    """Single knowledge entry."""
    entry_id: str
    name: str
    connector_type: str  # file | url | text
    content: str
    metadata: dict = field(default_factory=dict)
    tags: list[str] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    content_hash: str = ""
    size_bytes: int = 0
    enabled: bool = True

    def __post_init__(self):
        if not self.content_hash:
            self.content_hash = hashlib.sha256(self.content.encode("utf-8")).hexdigest()[:16]
        if not self.size_bytes:
            self.size_bytes = len(self.content.encode("utf-8"))


class KnowledgeStore:
    """JSON-backed knowledge store with connector support.

    Supports three connector types:
    - file: Content loaded from a local file path
    - url: Content from a URL (stored as reference + cached content)
    - text: Inline text content

    Thread-safe CRUD operations with atomic writes.
    """

    def __init__(self, store_path: str = None):
        self._path = store_path or KNOWLEDGE_STORE_PATH
        self._entries: dict[str, KnowledgeEntry] = {}
        self._lock = threading.Lock()
        self._load()

    def _load(self) -> None:
        """Load entries from JSON file."""
        if os.path.exists(self._path):
            try:
                with open(self._path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                for raw in data.get("entries", []):
                    entry = KnowledgeEntry(**raw)
                    self._entries[entry.entry_id] = entry
                logger.info("KnowledgeStore loaded %d entries", len(self._entries))
            except Exception as e:
                logger.warning("KnowledgeStore load failed: %s", e)
                self._entries = {}

    def _save(self) -> None:
        """Save entries to JSON file atomically."""
        try:
            data = {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "entries": [asdict(e) for e in self._entries.values()],
            }
            atomic_write_json(self._path, data)
        except Exception as e:
            logger.error("KnowledgeStore save failed: %s", e)

    def add(self, name: str, connector_type: str, content: str,
            metadata: dict = None, tags: list[str] = None) -> KnowledgeEntry:
        """Add a knowledge entry. Returns the created entry."""
        if connector_type not in ("file", "url", "text"):
            raise ValueError(f"Invalid connector_type: {connector_type}. Must be file|url|text")

        entry_id = hashlib.sha256(
            f"{name}:{connector_type}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:12]

        entry = KnowledgeEntry(
            entry_id=entry_id,
            name=name,
            connector_type=connector_type,
            content=content,
            metadata=metadata or {},
            tags=tags or [],
        )

        with self._lock:
            self._entries[entry_id] = entry
            self._save()

        logger.info("Knowledge entry added: %s (%s, %d bytes)", entry_id, connector_type, entry.size_bytes)
        return entry

    def get(self, entry_id: str) -> Optional[KnowledgeEntry]:
        """Get a single entry by ID."""
        with self._lock:
            return self._entries.get(entry_id)

    def update(self, entry_id: str, name: str = None, content: str = None,
               metadata: dict = None, tags: list[str] = None,
               enabled: bool = None) -> Optional[KnowledgeEntry]:
        """Update an existing entry. Returns updated entry or None."""
        with self._lock:
            entry = self._entries.get(entry_id)
            if not entry:
                return None

            if name is not None:
                entry.name = name
            if content is not None:
                entry.content = content
                entry.content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
                entry.size_bytes = len(content.encode("utf-8"))
            if metadata is not None:
                entry.metadata = metadata
            if tags is not None:
                entry.tags = tags
            if enabled is not None:
                entry.enabled = enabled
            entry.updated_at = datetime.now(timezone.utc).isoformat()

            self._save()
            return entry

    def delete(self, entry_id: str) -> bool:
        """Delete an entry. Returns True if deleted."""
        with self._lock:
            if entry_id not in self._entries:
                return False
            del self._entries[entry_id]
            self._save()
            return True

    def list(self, connector_type: str = None, tag: str = None,
             enabled_only: bool = True, search: str = None,
             limit: int = 50, offset: int = 0) -> tuple[list[dict], int]:
        """List entries with filters. Returns (entries, total_count)."""
        with self._lock:
            items = list(self._entries.values())

        if enabled_only:
            items = [e for e in items if e.enabled]
        if connector_type:
            items = [e for e in items if e.connector_type == connector_type]
        if tag:
            items = [e for e in items if tag in e.tags]
        if search:
            q = search.lower()
            items = [e for e in items if q in e.name.lower() or q in e.content.lower()]

        total = len(items)
        items.sort(key=lambda e: e.updated_at, reverse=True)
        items = items[offset:offset + limit]

        return [asdict(e) for e in items], total

    def search_by_tags(self, tags: list[str]) -> list[dict]:
        """Find entries matching any of the given tags."""
        with self._lock:
            items = [
                e for e in self._entries.values()
                if e.enabled and any(t in e.tags for t in tags)
            ]
        return [asdict(e) for e in items]

    def get_for_mission(self, mission_tags: list[str] = None,
                        entry_ids: list[str] = None) -> list[dict]:
        """Get knowledge entries relevant to a mission.

        Selects by explicit entry_ids or by tag matching.
        Returns list of {entry_id, name, connector_type, content, metadata}.
        """
        with self._lock:
            results = []

            if entry_ids:
                for eid in entry_ids:
                    entry = self._entries.get(eid)
                    if entry and entry.enabled:
                        results.append(entry)

            if mission_tags:
                for entry in self._entries.values():
                    if entry.enabled and entry not in results:
                        if any(t in entry.tags for t in mission_tags):
                            results.append(entry)

        return [
            {
                "entry_id": e.entry_id,
                "name": e.name,
                "connector_type": e.connector_type,
                "content": e.content,
                "metadata": e.metadata,
            }
            for e in results
        ]

    @property
    def count(self) -> int:
        with self._lock:
            return len(self._entries)

    def stats(self) -> dict:
        """Return store statistics."""
        with self._lock:
            items = list(self._entries.values())

        by_type = {}
        for e in items:
            by_type[e.connector_type] = by_type.get(e.connector_type, 0) + 1

        total_bytes = sum(e.size_bytes for e in items)
        enabled = sum(1 for e in items if e.enabled)

        return {
            "total_entries": len(items),
            "enabled": enabled,
            "disabled": len(items) - enabled,
            "by_connector_type": by_type,
            "total_bytes": total_bytes,
        }
