"""Multi-source allowlist — B-009.

YAML-based allowlist for controlling which sources, callers, and
IP ranges can invoke missions. Integrates with policy engine.
"""
import logging
import os
import re
import threading
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

import yaml


def _safe_filename(name: str) -> str:
    """Validate name is safe for use as a filename (no path traversal)."""
    if not name or not re.match(r'^[a-zA-Z0-9_\-]+$', name):
        raise ValueError(f"Invalid name: must be alphanumeric/underscore/hyphen, got '{name}'")
    return name

logger = logging.getLogger("mcc.allowlist")

_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
ALLOWLISTS_DIR = str(_ROOT / "config" / "allowlists")


@dataclass
class AllowlistEntry:
    """Single allowlist entry."""
    name: str
    source_type: str  # caller_source | caller_id | caller_role | ip_range
    values: list[str] = field(default_factory=list)
    description: str = ""
    enabled: bool = True


class AllowlistStore:
    """YAML-based multi-source allowlist store.

    Manages allowlist entries in config/allowlists/*.yaml.
    Thread-safe CRUD operations with atomic writes.
    """

    def __init__(self, allowlists_dir: str = None):
        self._dir = allowlists_dir or ALLOWLISTS_DIR
        self._entries: list[AllowlistEntry] = []
        self._lock = threading.Lock()
        self.load()

    def load(self) -> int:
        """Load all allowlist YAML files. Returns count loaded."""
        self._entries = []
        path = Path(self._dir)
        if not path.exists():
            return 0

        for yaml_file in sorted(path.glob("*.yaml")):
            try:
                with open(yaml_file, "r", encoding="utf-8") as f:
                    raw = yaml.safe_load(f)
                if raw and isinstance(raw, dict):
                    entry = AllowlistEntry(
                        name=raw.get("name", yaml_file.stem),
                        source_type=raw.get("source_type", "caller_source"),
                        values=raw.get("values", []),
                        description=raw.get("description", ""),
                        enabled=raw.get("enabled", True),
                    )
                    self._entries.append(entry)
            except (yaml.YAMLError, TypeError) as e:
                logger.error("Failed to load allowlist %s: %s", yaml_file.name, e)

        logger.info("Loaded %d allowlist entries", len(self._entries))
        return len(self._entries)

    @property
    def entries(self) -> list[AllowlistEntry]:
        return list(self._entries)

    def get(self, name: str) -> Optional[AllowlistEntry]:
        """Get allowlist entry by name."""
        for entry in self._entries:
            if entry.name == name:
                return entry
        return None

    def check(self, source_type: str, value: str) -> bool:
        """Check if a value is allowed for the given source type.

        Returns True if:
        - No enabled allowlists exist for this source_type (open by default)
        - Value matches at least one enabled allowlist entry
        """
        relevant = [e for e in self._entries
                     if e.source_type == source_type and e.enabled]
        if not relevant:
            return True  # No restrictions = allowed

        for entry in relevant:
            if value in entry.values:
                return True
            # Wildcard support
            if "*" in entry.values:
                return True
            # Prefix matching for patterns like "api.*"
            for pattern in entry.values:
                if pattern.endswith("*") and value.startswith(pattern[:-1]):
                    return True

        return False

    def check_caller(self, caller: dict) -> dict:
        """Check all allowlist dimensions for a caller.

        Args:
            caller: dict with caller_id, caller_role, source keys

        Returns:
            dict with allowed (bool), denied_by (list of entry names)
        """
        denied_by = []
        for source_type in ["caller_source", "caller_id", "caller_role"]:
            # Map source_type to caller dict key
            key_map = {
                "caller_source": "source",
                "caller_id": "caller_id",
                "caller_role": "caller_role",
            }
            caller_key = key_map.get(source_type, source_type)
            caller_value = caller.get(caller_key, "")

            if caller_value and not self.check(source_type, caller_value):
                # Find which entries denied
                relevant = [e for e in self._entries
                             if e.source_type == source_type and e.enabled]
                denied_by.extend(e.name for e in relevant)

        return {
            "allowed": len(denied_by) == 0,
            "denied_by": denied_by,
        }

    def create(self, data: dict) -> AllowlistEntry:
        """Create a new allowlist entry. Writes YAML, reloads."""
        name = _safe_filename(data.get("name", ""))

        with self._lock:
            if self.get(name):
                raise ValueError(f"Allowlist '{name}' already exists")

            entry = AllowlistEntry(
                name=name,
                source_type=data.get("source_type", "caller_source"),
                values=data.get("values", []),
                description=data.get("description", ""),
                enabled=data.get("enabled", True),
            )
            self._write_yaml(name, asdict(entry))
            self.load()
        return self.get(name)

    def update(self, name: str, data: dict) -> AllowlistEntry:
        """Update an existing allowlist entry."""
        name = _safe_filename(name)
        with self._lock:
            if not self.get(name):
                raise KeyError(f"Allowlist '{name}' not found")

            merged = {"name": name, **data}
            entry = AllowlistEntry(
                name=name,
                source_type=merged.get("source_type", "caller_source"),
                values=merged.get("values", []),
                description=merged.get("description", ""),
                enabled=merged.get("enabled", True),
            )
            self._write_yaml(name, asdict(entry))
            self.load()
        return self.get(name)

    def delete(self, name: str) -> bool:
        """Delete an allowlist entry."""
        name = _safe_filename(name)
        with self._lock:
            if not self.get(name):
                raise KeyError(f"Allowlist '{name}' not found")
            base = Path(self._dir).resolve()
            yaml_path = (base / f"{name}.yaml").resolve()
            if not str(yaml_path).startswith(str(base) + os.sep):
                raise ValueError(f"Path traversal blocked: {name}")
            if yaml_path.exists():
                yaml_path.unlink()
            self.load()
        return True

    def _write_yaml(self, name: str, data: dict) -> None:
        """Atomic YAML write (D-071 pattern)."""
        path = Path(self._dir).resolve()
        path.mkdir(parents=True, exist_ok=True)
        target = (path / f"{name}.yaml").resolve()
        if not str(target).startswith(str(path) + os.sep):
            raise ValueError(f"Path traversal blocked: {name}")
        tmp = target.with_suffix(".yaml.tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                yaml.safe_dump(data, f, default_flow_style=False, allow_unicode=True)
                f.flush()
                os.fsync(f.fileno())
            tmp.replace(target)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise

    def to_dict(self) -> list[dict]:
        """Serialize all entries for API."""
        return [asdict(e) for e in self._entries]
