"""Mission template store — D-119.

File-based CRUD for mission templates.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from templates.schema import MissionTemplate, TemplateParameter, MissionConfig

logger = logging.getLogger("mcc.templates")


class TemplateStore:
    """File-based template storage."""

    def __init__(self, templates_dir: Path | None = None):
        self._dir = templates_dir or Path(__file__).resolve().parent.parent.parent / "config" / "templates"
        self._dir.mkdir(parents=True, exist_ok=True)

    def list(self) -> list[dict]:
        """List all templates."""
        templates = []
        for f in sorted(self._dir.glob("*.json")):
            tmpl = self._load(f)
            if tmpl:
                templates.append(tmpl.to_dict())
        return templates

    def get(self, template_id: str) -> Optional[MissionTemplate]:
        """Get template by ID."""
        path = self._dir / f"{template_id}.json"
        if not path.exists():
            return None
        return self._load(path)

    def create(self, data: dict) -> MissionTemplate:
        """Create a new template."""
        params = [
            TemplateParameter(
                name=p["name"], type=p.get("type", "string"),
                required=p.get("required", True), description=p.get("description", ""),
                default=p.get("default"),
            )
            for p in data.get("parameters", [])
        ]
        mc = data.get("mission_config", {})
        tmpl = MissionTemplate(
            name=data.get("name", "Untitled"),
            description=data.get("description", ""),
            version=data.get("version", "1.0.0"),
            author=data.get("author", ""),
            status=data.get("status", "draft"),
            parameters=params,
            mission_config=MissionConfig(
                goal_template=mc.get("goal_template", ""),
                specialist=mc.get("specialist", "analyst"),
                provider=mc.get("provider", "gpt-4o"),
                max_stages=mc.get("max_stages", 5),
                timeout_minutes=mc.get("timeout_minutes", 30),
            ),
        )
        self._save(tmpl)
        logger.info("Template created: %s (%s)", tmpl.name, tmpl.id)
        return tmpl

    def update(self, template_id: str, data: dict) -> Optional[MissionTemplate]:
        """Update existing template."""
        tmpl = self.get(template_id)
        if not tmpl:
            return None
        for key in ("name", "description", "version", "author", "status"):
            if key in data:
                setattr(tmpl, key, data[key])
        tmpl.updated_at = datetime.now(timezone.utc).isoformat()
        self._save(tmpl)
        return tmpl

    def delete(self, template_id: str) -> bool:
        """Delete a template."""
        path = self._dir / f"{template_id}.json"
        if not path.exists():
            return False
        path.unlink()
        logger.info("Template deleted: %s", template_id)
        return True

    def _save(self, tmpl: MissionTemplate) -> None:
        path = self._dir / f"{tmpl.id}.json"
        path.write_text(json.dumps(tmpl.to_dict(), indent=2, ensure_ascii=False), encoding="utf-8")

    def _load(self, path: Path) -> Optional[MissionTemplate]:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            params = [
                TemplateParameter(
                    name=p["name"], type=p.get("type", "string"),
                    required=p.get("required", True), description=p.get("description", ""),
                    default=p.get("default"),
                )
                for p in data.get("parameters", [])
            ]
            mc = data.get("mission_config", {})
            return MissionTemplate(
                id=data["id"], name=data["name"], description=data.get("description", ""),
                version=data.get("version", "1.0.0"), author=data.get("author", ""),
                status=data.get("status", "draft"), parameters=params,
                mission_config=MissionConfig(
                    goal_template=mc.get("goal_template", ""),
                    specialist=mc.get("specialist", "analyst"),
                    provider=mc.get("provider", "gpt-4o"),
                    max_stages=mc.get("max_stages", 5),
                    timeout_minutes=mc.get("timeout_minutes", 30),
                ),
                created_at=data.get("created_at", ""),
                updated_at=data.get("updated_at", ""),
            )
        except (json.JSONDecodeError, KeyError) as e:
            logger.warning("Failed to load template %s: %s", path, e)
            return None
