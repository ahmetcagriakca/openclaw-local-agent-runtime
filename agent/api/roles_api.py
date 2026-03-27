"""Roles API — expose agent role definitions and skills."""
from fastapi import APIRouter
from pydantic import BaseModel, Field

from api.schemas import DataQuality, ResponseMeta
from mission.role_registry import ROLE_REGISTRY
from mission.specialists import SPECIALIST_PROMPTS

router = APIRouter(tags=["roles"])


class RoleInfo(BaseModel):
    name: str
    defaultSkill: str = ""
    allowedSkills: list[str] = Field(default_factory=list)
    toolPolicy: str = ""
    model: str = ""
    tools: list[str] = Field(default_factory=list)
    discoveryRights: str = ""
    maxFileReads: int = 0
    promptPreview: str = ""


class RolesResponse(BaseModel):
    meta: ResponseMeta
    roles: dict[str, RoleInfo] = Field(default_factory=dict)


@router.get("/roles", response_model=RolesResponse)
async def list_roles():
    """Return all 9 canonical agent roles with skills, tools, and prompt previews."""
    roles: dict[str, RoleInfo] = {}

    for role_id, role_def in ROLE_REGISTRY.items():
        prompt = SPECIALIST_PROMPTS.get(role_id, "")
        preview = prompt[:300].rstrip() if prompt else ""
        if len(prompt) > 300:
            preview += "..."

        allowed_tools = role_def.get("allowedTools")
        tool_list: list[str] = []
        if allowed_tools is None:
            tool_list = ["(all 24 tools)"]
        elif isinstance(allowed_tools, list):
            tool_list = allowed_tools

        roles[role_id] = RoleInfo(
            name=role_def.get("displayName", role_id),
            defaultSkill=role_def.get("defaultSkill", ""),
            allowedSkills=role_def.get("allowedSkills", []),
            toolPolicy=role_def.get("toolPolicy", ""),
            model=role_def.get("preferredModel", ""),
            tools=tool_list,
            discoveryRights=role_def.get("discoveryRights", ""),
            maxFileReads=role_def.get("maxFileReads", 0),
            promptPreview=preview,
        )

    meta = ResponseMeta(dataQuality=DataQuality.FRESH)
    return RolesResponse(meta=meta, roles=roles)
