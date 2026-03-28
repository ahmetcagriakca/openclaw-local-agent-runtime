"""Plugin manifest validation — D-118.

Validates plugin manifest.json files against the contract schema.
"""
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


@dataclass
class HandlerSpec:
    event_type: str
    handler: str  # function name in handler module
    priority: int = 500


@dataclass
class PluginManifest:
    name: str
    version: str
    description: str
    author: str
    handlers: list[HandlerSpec] = field(default_factory=list)
    config_schema: dict = field(default_factory=dict)


def load_manifest(manifest_path: Path) -> Optional[PluginManifest]:
    """Load and validate a plugin manifest.json. Returns None on error."""
    try:
        data = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None

    required = ["name", "version", "description", "author"]
    if not all(k in data for k in required):
        return None

    handlers = []
    for h in data.get("handlers", []):
        if "event_type" not in h or "handler" not in h:
            continue
        handlers.append(HandlerSpec(
            event_type=h["event_type"],
            handler=h["handler"],
            priority=h.get("priority", 500),
        ))

    return PluginManifest(
        name=data["name"],
        version=data["version"],
        description=data["description"],
        author=data["author"],
        handlers=handlers,
        config_schema=data.get("config_schema", {}),
    )
