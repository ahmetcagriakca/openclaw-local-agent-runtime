"""Feature flags module — D-102 context isolation wire-up.

Loads feature flags from config/features.json.
Supports runtime reload and safe defaults.
Uses atomic_write_json for persistence (D-071).
"""
import json
import logging
import os
from pathlib import Path

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.config.feature_flags")

# ── Paths ────────────────────────────────────────────────────────

# agent/config/feature_flags.py -> agent/ -> project root
_OC_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))
_FEATURES_PATH = _OC_ROOT / "config" / "features.json"

# ── Defaults ─────────────────────────────────────────────────────

_DEFAULTS: dict[str, bool] = {
    "CONTEXT_ISOLATION_ENABLED": False,
}


# ── Module State ─────────────────────────────────────────────────

_flags: dict[str, bool] = {}
_loaded: bool = False


def _load() -> dict[str, bool]:
    """Load flags from disk, merging with defaults."""
    global _flags, _loaded
    result = dict(_DEFAULTS)
    if _FEATURES_PATH.exists():
        try:
            raw = json.loads(_FEATURES_PATH.read_text(encoding="utf-8"))
            if isinstance(raw, dict):
                for key, default_val in _DEFAULTS.items():
                    val = raw.get(key, default_val)
                    result[key] = bool(val)
                # Preserve unknown flags from file (forward-compat)
                for key, val in raw.items():
                    if key not in result:
                        result[key] = bool(val)
            logger.info("Feature flags loaded from %s", _FEATURES_PATH)
        except Exception as exc:
            logger.warning("Failed to load features.json, using defaults: %s", exc)
    else:
        logger.info("features.json not found, using defaults")
    _flags = result
    _loaded = True
    return result


def get_flag(name: str) -> bool:
    """Get a feature flag value. Returns default if not loaded or unknown."""
    if not _loaded:
        _load()
    return _flags.get(name, _DEFAULTS.get(name, False))


def get_all_flags() -> dict[str, bool]:
    """Get all feature flag values."""
    if not _loaded:
        _load()
    return dict(_flags)


def set_flag(name: str, value: bool) -> None:
    """Set a feature flag and persist to disk (atomic write, D-071)."""
    if not _loaded:
        _load()
    _flags[name] = bool(value)
    atomic_write_json(_FEATURES_PATH, _flags)
    logger.info("Feature flag %s set to %s", name, value)


def reload() -> dict[str, bool]:
    """Force reload flags from disk."""
    global _loaded
    _loaded = False
    return _load()


def reset() -> None:
    """Reset module state (for testing)."""
    global _flags, _loaded
    _flags = {}
    _loaded = False
