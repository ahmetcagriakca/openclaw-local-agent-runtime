#!/usr/bin/env python3
"""Template/Plugin Scaffolding CLI — B-109 Sprint 50.

Generates preset template JSON or plugin manifest from command-line flags.
Validates specialist against role registry.

Usage:
    python tools/scaffold_template.py --name "My Template" --specialist analyst --goal "Do analysis"
    python tools/scaffold_template.py --plugin --name "My Plugin" --events mission.completed stage.failed
"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

# Add agent/ to path for imports
AGENT_DIR = Path(__file__).resolve().parent.parent / "agent"
sys.path.insert(0, str(AGENT_DIR))

from mission.role_registry import ROLE_REGISTRY

TEMPLATES_DIR = Path(__file__).resolve().parent.parent / "config" / "templates"
PLUGINS_DIR = Path(__file__).resolve().parent.parent / "config" / "plugins"

VALID_ROLES = set(ROLE_REGISTRY.keys())


def validate_specialist(specialist: str) -> bool:
    """Validate specialist against role registry."""
    return specialist in VALID_ROLES


def scaffold_template(
    name: str,
    specialist: str,
    goal: str,
    max_stages: int = 5,
    timeout_minutes: int = 15,
    provider: str = "gpt-4o",
    parameters: list[dict] | None = None,
    description: str = "",
) -> dict:
    """Generate a preset template JSON structure."""
    if not validate_specialist(specialist):
        raise ValueError(
            f"Invalid specialist '{specialist}'. Valid: {sorted(VALID_ROLES)}"
        )

    template_id = f"preset_{name.lower().replace(' ', '_').replace('-', '_')}"
    now = datetime.now(timezone.utc).isoformat()

    return {
        "id": template_id,
        "name": name,
        "description": description or f"Auto-generated template: {name}",
        "version": "1.0.0",
        "author": "Vezir CLI",
        "status": "draft",
        "parameters": parameters or [],
        "mission_config": {
            "goal_template": goal,
            "specialist": specialist,
            "provider": provider,
            "max_stages": max_stages,
            "timeout_minutes": timeout_minutes,
        },
        "created_at": now,
        "updated_at": now,
    }


def scaffold_plugin(
    name: str,
    events: list[str] | None = None,
    description: str = "",
) -> dict:
    """Generate a plugin manifest JSON structure."""
    plugin_id = f"plugin_{name.lower().replace(' ', '_').replace('-', '_')}"
    now = datetime.now(timezone.utc).isoformat()

    return {
        "id": plugin_id,
        "name": name,
        "description": description or f"Auto-generated plugin: {name}",
        "version": "1.0.0",
        "author": "Vezir CLI",
        "status": "draft",
        "hooks": {
            "on_mission_start": None,
            "on_stage_complete": None,
            "on_mission_complete": None,
            "on_mission_failed": None,
        },
        "event_subscriptions": events or [],
        "config": {},
        "created_at": now,
        "updated_at": now,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Vezir Template/Plugin Scaffolding CLI (B-109)"
    )
    parser.add_argument("--name", required=True, help="Template or plugin name")
    parser.add_argument("--plugin", action="store_true", help="Generate plugin manifest")
    parser.add_argument("--specialist", default="analyst", help="Specialist role")
    parser.add_argument("--goal", default="", help="Mission goal template")
    parser.add_argument("--max-stages", type=int, default=5, help="Max stages")
    parser.add_argument("--timeout", type=int, default=15, help="Timeout in minutes")
    parser.add_argument("--provider", default="gpt-4o", help="LLM provider")
    parser.add_argument("--events", nargs="*", default=[], help="Event subscriptions (plugin mode)")
    parser.add_argument("--description", default="", help="Description")
    parser.add_argument("--output", help="Output file path (default: config dir)")
    parser.add_argument("--dry-run", action="store_true", help="Print without writing")

    args = parser.parse_args()

    if args.plugin:
        result = scaffold_plugin(
            name=args.name,
            events=args.events,
            description=args.description,
        )
        default_dir = PLUGINS_DIR
        filename = f"{result['id']}.json"
    else:
        if not args.goal:
            parser.error("--goal is required for template scaffolding")
        result = scaffold_template(
            name=args.name,
            specialist=args.specialist,
            goal=args.goal,
            max_stages=args.max_stages,
            timeout_minutes=args.timeout,
            provider=args.provider,
            description=args.description,
        )
        default_dir = TEMPLATES_DIR
        filename = f"{result['id']}.json"

    output = json.dumps(result, indent=2, ensure_ascii=False)

    if args.dry_run:
        print(output)
        return

    out_path = Path(args.output) if args.output else default_dir / filename
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(output, encoding="utf-8")
    print(f"Generated: {out_path}")


if __name__ == "__main__":
    main()
