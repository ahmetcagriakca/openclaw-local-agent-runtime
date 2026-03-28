"""Mission template schema — D-119.

Defines template structure and parameter validation.
"""
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any
import uuid


@dataclass
class TemplateParameter:
    name: str
    type: str  # string, number, boolean, array
    required: bool = True
    description: str = ""
    default: Any = None


@dataclass
class MissionConfig:
    goal_template: str
    specialist: str = "analyst"
    provider: str = "gpt-4o"
    max_stages: int = 5
    timeout_minutes: int = 30


@dataclass
class MissionTemplate:
    id: str = field(default_factory=lambda: f"tmpl_{uuid.uuid4().hex[:12]}")
    name: str = ""
    description: str = ""
    version: str = "1.0.0"
    author: str = ""
    status: str = "draft"  # draft, published, archived
    parameters: list[TemplateParameter] = field(default_factory=list)
    mission_config: MissionConfig = field(default_factory=MissionConfig)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "version": self.version,
            "author": self.author,
            "status": self.status,
            "parameters": [
                {"name": p.name, "type": p.type, "required": p.required,
                 "description": p.description, "default": p.default}
                for p in self.parameters
            ],
            "mission_config": {
                "goal_template": self.mission_config.goal_template,
                "specialist": self.mission_config.specialist,
                "provider": self.mission_config.provider,
                "max_stages": self.mission_config.max_stages,
                "timeout_minutes": self.mission_config.timeout_minutes,
            },
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def render_goal(self, params: dict) -> str:
        """Render goal template with provided parameters."""
        goal = self.mission_config.goal_template
        for p in self.parameters:
            value = params.get(p.name, p.default)
            goal = goal.replace(f"{{{p.name}}}", str(value) if value is not None else "")
        return goal

    def validate_params(self, params: dict) -> list[str]:
        """Validate parameters. Returns list of errors (empty = valid)."""
        errors = []
        for p in self.parameters:
            if p.required and p.name not in params:
                errors.append(f"Missing required parameter: {p.name}")
        return errors
