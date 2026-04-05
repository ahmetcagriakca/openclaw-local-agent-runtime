"""Plugin marketplace store — D-136, Sprint 59 Task 59.1.

Manages plugin metadata, search/filter, install state tracking.
Indexes plugins from PluginRegistry discover() + manifest validation.
"""
from __future__ import annotations

import logging
import threading
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.plugin_marketplace")


@dataclass
class PluginEntry:
    """Single plugin entry in the marketplace."""

    plugin_id: str
    name: str
    version: str
    description: str
    author: str
    status: str = "available"  # available | installed | enabled | disabled
    capabilities: list[str] = field(default_factory=list)
    risk_tier: str = "high"  # low | medium | high
    source: str = "local"
    trust_status: str = "unknown"  # unknown | trusted | untrusted
    category: str = "general"
    tags: list[str] = field(default_factory=list)
    installed_at: Optional[str] = None
    updated_at: Optional[str] = None


# Valid state transitions per D-136
_VALID_TRANSITIONS = {
    "available": ["installed"],
    "installed": ["enabled", "disabled", "available"],
    "enabled": ["disabled", "available"],
    "disabled": ["enabled", "available"],
}


class PluginMarketplaceStore:
    """Plugin marketplace store per D-136 contract.

    Discovers plugins from plugin directories, validates manifests,
    tracks install state, supports search/filter/CRUD.
    Thread-safe with atomic JSON persistence.
    """

    def __init__(self, store_path: Path | str | None = None, plugins_dir: Path | str | None = None):
        if store_path is None:
            root = Path(__file__).resolve().parent.parent.parent
            store_path = root / "logs" / "plugin-marketplace.json"
        if plugins_dir is None:
            plugins_dir = Path(__file__).resolve().parent.parent / "plugins"
        self._path = Path(store_path)
        self._plugins_dir = Path(plugins_dir)
        self._lock = threading.Lock()
        self._entries: dict[str, PluginEntry] = {}
        self._events: list[dict] = []
        self._load()

    def _load(self) -> None:
        if self._path.exists():
            try:
                import json

                data = json.loads(self._path.read_text(encoding="utf-8"))
                for pid, entry_data in data.get("plugins", {}).items():
                    self._entries[pid] = PluginEntry(**entry_data)
                self._events = data.get("events", [])
                logger.info("PluginMarketplaceStore loaded %d plugins", len(self._entries))
            except Exception as e:
                logger.warning("PluginMarketplaceStore load failed: %s", e)
                self._entries = {}
                self._events = []

    def _save(self) -> None:
        try:
            atomic_write_json(self._path, {
                "version": 1,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "plugins": {pid: asdict(entry) for pid, entry in self._entries.items()},
                "events": self._events[-1000:],  # keep last 1000 events
            })
        except Exception as e:
            logger.error("PluginMarketplaceStore save failed: %s", e)

    def _log_event(self, action: str, plugin_id: str, detail: str = "") -> None:
        self._events.append({
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "action": action,
            "plugin_id": plugin_id,
            "detail": detail,
        })

    # -- Discovery --

    def discover_and_index(self) -> int:
        """Discover plugins from plugins_dir and index into store.

        Scans for directories with manifest.json, validates via load_manifest,
        and creates/updates entries. Returns count of discovered plugins.
        """
        from plugins.manifest import load_manifest

        with self._lock:
            discovered = 0
            if not self._plugins_dir.is_dir():
                return 0

            for child in sorted(self._plugins_dir.iterdir()):
                manifest_path = child / "manifest.json"
                if not child.is_dir() or not manifest_path.exists():
                    continue

                manifest = load_manifest(manifest_path)
                pid = child.name

                if manifest is None:
                    # Invalid manifest → list with risk_tier=high, trust_status=unknown per D-136
                    if pid not in self._entries:
                        self._entries[pid] = PluginEntry(
                            plugin_id=pid,
                            name=pid,
                            version="0.0.0",
                            description="Invalid manifest",
                            author="unknown",
                            risk_tier="high",
                            trust_status="unknown",
                        )
                        self._log_event("discover_invalid", pid, "Invalid manifest")
                    discovered += 1
                    continue

                # Read extended metadata from manifest JSON
                import json

                try:
                    raw = json.loads(manifest_path.read_text(encoding="utf-8"))
                except (json.JSONDecodeError, OSError):
                    raw = {}

                existing = self._entries.get(pid)
                status = existing.status if existing else "available"

                self._entries[pid] = PluginEntry(
                    plugin_id=pid,
                    name=manifest.name,
                    version=manifest.version,
                    description=manifest.description,
                    author=manifest.author,
                    status=status,
                    capabilities=raw.get("capabilities", []),
                    risk_tier=raw.get("risk_tier", "high"),
                    source=raw.get("source", "local"),
                    trust_status=raw.get("trust_status", "unknown"),
                    category=raw.get("category", "general"),
                    tags=raw.get("tags", []),
                    installed_at=existing.installed_at if existing else None,
                    updated_at=datetime.now(timezone.utc).isoformat(),
                )

                if not existing:
                    self._log_event("discover", pid)

                discovered += 1

            self._save()
            logger.info("Discovered and indexed %d plugins", discovered)
            return discovered

    # -- CRUD --

    def get(self, plugin_id: str) -> Optional[PluginEntry]:
        with self._lock:
            return self._entries.get(plugin_id)

    def list_all(self) -> list[PluginEntry]:
        with self._lock:
            return list(self._entries.values())

    def update_status(self, plugin_id: str, new_status: str) -> bool:
        """Update plugin status with valid transition check per D-136."""
        with self._lock:
            entry = self._entries.get(plugin_id)
            if entry is None:
                return False

            valid = _VALID_TRANSITIONS.get(entry.status, [])
            if new_status not in valid:
                logger.warning(
                    "Invalid transition %s → %s for plugin %s",
                    entry.status, new_status, plugin_id,
                )
                return False

            old_status = entry.status
            entry.status = new_status
            now = datetime.now(timezone.utc).isoformat()
            entry.updated_at = now

            if new_status == "installed":
                entry.installed_at = now
            elif new_status == "available":
                entry.installed_at = None

            self._log_event("status_change", plugin_id, f"{old_status} → {new_status}")
            self._save()
            return True

    def update_config(self, plugin_id: str, config: dict) -> bool:
        """Update plugin configuration. Returns False if plugin not found."""
        with self._lock:
            entry = self._entries.get(plugin_id)
            if entry is None:
                return False
            entry.updated_at = datetime.now(timezone.utc).isoformat()
            self._log_event("config_update", plugin_id)
            self._save()
            return True

    # -- Search & Filter --

    def search(self, query: str) -> list[PluginEntry]:
        """Search plugins by name or description (case-insensitive)."""
        q = query.lower()
        with self._lock:
            return [
                e for e in self._entries.values()
                if q in e.name.lower() or q in e.description.lower()
            ]

    def filter_by_status(self, status: str) -> list[PluginEntry]:
        """Filter plugins by status."""
        with self._lock:
            return [e for e in self._entries.values() if e.status == status]

    def filter_by_category(self, category: str) -> list[PluginEntry]:
        """Filter plugins by category."""
        with self._lock:
            return [e for e in self._entries.values() if e.category == category]

    def filter_by_tag(self, tag: str) -> list[PluginEntry]:
        """Filter plugins by tag."""
        with self._lock:
            return [e for e in self._entries.values() if tag in e.tags]

    def filter(self, status: Optional[str] = None, category: Optional[str] = None, query: Optional[str] = None) -> list[PluginEntry]:
        """Combined filter with optional status, category, and search query."""
        with self._lock:
            results = list(self._entries.values())

        if status:
            results = [e for e in results if e.status == status]
        if category:
            results = [e for e in results if e.category == category]
        if query:
            q = query.lower()
            results = [e for e in results if q in e.name.lower() or q in e.description.lower()]
        return results

    # -- Stats & Events --

    def stats(self) -> dict:
        """Return marketplace statistics."""
        with self._lock:
            entries = list(self._entries.values())
            return {
                "total": len(entries),
                "available": sum(1 for e in entries if e.status == "available"),
                "installed": sum(1 for e in entries if e.status == "installed"),
                "enabled": sum(1 for e in entries if e.status == "enabled"),
                "disabled": sum(1 for e in entries if e.status == "disabled"),
                "by_category": _count_by(entries, "category"),
                "by_risk_tier": _count_by(entries, "risk_tier"),
            }

    def events(self, limit: int = 50) -> list[dict]:
        """Return recent marketplace events."""
        with self._lock:
            return list(reversed(self._events[-limit:]))


def _count_by(entries: list[PluginEntry], attr: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for e in entries:
        val = getattr(e, attr, "unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts
