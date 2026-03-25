"""Capability checker service — reads config/capabilities.json.

GPT Fix 4: Tri-state CapabilityStatus (available/unavailable/unknown).
D-068: Missing/corrupt manifest → all capabilities UNKNOWN, no crash.
"""
import json
import os
from pathlib import Path

from api.schemas import CapabilityEntry, CapabilityStatus


class CapabilityChecker:
    def __init__(self, manifest_path: Path | str):
        self._path = Path(manifest_path)
        self._capabilities: dict[str, dict] = {}
        self._status: str = "unknown"
        self._mtime: float = 0.0
        self.refresh()

    def refresh(self) -> None:
        """Re-read manifest from disk (mtime caching)."""
        if not self._path.exists():
            self._capabilities = {}
            self._status = "missing"
            return
        try:
            mtime = os.path.getmtime(str(self._path))
            if mtime == self._mtime and self._capabilities:
                return  # mtime unchanged
            data = json.loads(self._path.read_text(encoding="utf-8"))
            self._capabilities = data.get("capabilities", {})
            self._status = "ok"
            self._mtime = mtime
        except (json.JSONDecodeError, UnicodeDecodeError):
            self._capabilities = {}
            self._status = "degraded"

    def get_status(self, name: str) -> CapabilityStatus:
        """Get capability status — tri-state.

        Manifest missing/corrupt → UNKNOWN.
        Capability not in manifest → UNAVAILABLE.
        """
        if self._status in ("missing", "degraded"):
            return CapabilityStatus.UNKNOWN
        entry = self._capabilities.get(name)
        if entry is None:
            return CapabilityStatus.UNAVAILABLE
        if entry.get("available", False):
            return CapabilityStatus.AVAILABLE
        return CapabilityStatus.UNAVAILABLE

    def is_available(self, name: str) -> bool:
        """Convenience: get_status() == AVAILABLE."""
        return self.get_status(name) == CapabilityStatus.AVAILABLE

    def get_all(self) -> dict[str, CapabilityEntry]:
        """Return all capabilities as schema objects."""
        result = {}
        for name, info in self._capabilities.items():
            available = info.get("available", False)
            result[name] = CapabilityEntry(
                name=name,
                status=(CapabilityStatus.AVAILABLE if available
                        else CapabilityStatus.UNAVAILABLE),
                since=info.get("since"),
            )
        return result

    def get_manifest_status(self) -> str:
        """Return manifest read status: ok | missing | degraded."""
        return self._status
