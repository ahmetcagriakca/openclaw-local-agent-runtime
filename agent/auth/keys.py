"""API key registry — D-117.

Loads API keys from config/auth.json. Validates Bearer tokens.
Fail-closed: missing config = deny all mutations.
Supports optional expires_at for token expiration.
"""
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


@dataclass
class ApiKey:
    key: str
    name: str
    role: str  # "operator" or "viewer"
    created: str
    expires_at: str = ""  # ISO 8601, empty = no expiration
    user_id: str = ""  # Sprint 40: user isolation scope


_keys: dict[str, ApiKey] = {}
_loaded = False


def _load_keys() -> None:
    global _keys, _loaded
    config_path = Path(__file__).resolve().parent.parent.parent / "config" / "auth.json"
    if not config_path.exists():
        _keys = {}
        _loaded = True
        return

    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
        _keys = {
            entry["key"]: ApiKey(
                key=entry["key"],
                name=entry["name"],
                role=entry["role"],
                created=entry.get("created", ""),
                expires_at=entry.get("expires_at", ""),
                user_id=entry.get("user_id", entry.get("name", "")),
            )
            for entry in data.get("keys", [])
        }
    except (json.JSONDecodeError, KeyError):
        _keys = {}
    _loaded = True


def validate_key(token: str) -> Optional[ApiKey]:
    """Validate an API key. Returns ApiKey if valid, None if invalid/expired."""
    if not _loaded:
        _load_keys()
    key = _keys.get(token)
    if key is None:
        return None
    if key.expires_at:
        try:
            exp = datetime.fromisoformat(key.expires_at.replace("Z", "+00:00"))
            if datetime.now(timezone.utc) > exp:
                return None  # Expired
        except ValueError:
            pass  # Invalid date format — treat as non-expiring
    return key


def is_auth_enabled() -> bool:
    """Check if auth is configured.

    Returns True (auth enforced) when:
    - Keys exist in auth.json, OR
    - No keys AND no VEZIR_AUTH_BYPASS=1 (fail-closed)

    Returns False (auth bypassed) ONLY when:
    - VEZIR_AUTH_BYPASS=1 is explicitly set in environment

    Env var check is always fresh (not cached) to avoid
    test-ordering issues where _loaded caches stale state.
    """
    import os
    # Bypass check — always fresh from env, never cached
    if os.environ.get("VEZIR_AUTH_BYPASS") == "1":
        return False
    # Keys loaded → auth enabled
    if not _loaded:
        _load_keys()
    # Keys exist → auth enabled; no keys + no bypass → fail-closed (auth enabled)
    return True


def reload_keys() -> None:
    """Force reload keys from config file."""
    global _loaded
    _loaded = False
    _load_keys()
