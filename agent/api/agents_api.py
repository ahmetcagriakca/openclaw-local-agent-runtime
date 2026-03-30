"""Agent Health & Capability View API — B-108 (Sprint 46).

Endpoints for provider liveness, role capability matrix, and agent
performance metrics. Exposes role registry + provider status as
structured data for dashboard consumption.
"""
from __future__ import annotations

import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter

logger = logging.getLogger("mcc.api.agents")

router = APIRouter(prefix="/agents", tags=["agents"])

_mission_store = None


def _get_store():
    global _mission_store
    if _mission_store is None:
        from persistence.mission_store import MissionStore
        _mission_store = MissionStore()
    return _mission_store


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [
            {"name": "role_registry", "ageMs": 0, "status": "fresh"},
            {"name": "mission_store", "ageMs": 0, "status": "fresh"},
        ],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _check_provider_liveness(name: str) -> dict:
    """Check if a provider is reachable by verifying env vars / connectivity."""
    if name == "openai":
        key = os.environ.get("OPENAI_API_KEY", "")
        return {
            "name": "OpenAI (GPT-4o)",
            "provider": "openai",
            "model": "gpt-4o",
            "status": "ok" if key else "unavailable",
            "detail": "API key configured" if key else "OPENAI_API_KEY not set",
        }
    elif name == "anthropic":
        key = os.environ.get("ANTHROPIC_API_KEY", "")
        return {
            "name": "Anthropic (Claude Sonnet)",
            "provider": "anthropic",
            "model": "claude-sonnet",
            "status": "ok" if key else "unavailable",
            "detail": "API key configured" if key else "ANTHROPIC_API_KEY not set",
        }
    elif name == "ollama":
        url = os.environ.get("OLLAMA_URL", "") or os.environ.get("OLLAMA_HOST", "")
        if url:
            try:
                import urllib.request
                req = urllib.request.Request(f"{url}/api/tags", method="GET")
                req.add_header("User-Agent", "vezir-health")
                with urllib.request.urlopen(req, timeout=3) as resp:
                    if resp.status == 200:
                        return {
                            "name": "Ollama (Local)",
                            "provider": "ollama",
                            "model": "local",
                            "status": "ok",
                            "detail": f"Reachable at {url}",
                        }
            except Exception as e:
                return {
                    "name": "Ollama (Local)",
                    "provider": "ollama",
                    "model": "local",
                    "status": "error",
                    "detail": f"Unreachable: {type(e).__name__}",
                }
        return {
            "name": "Ollama (Local)",
            "provider": "ollama",
            "model": "local",
            "status": "unavailable",
            "detail": "OLLAMA_URL not set",
        }
    return {"name": name, "provider": name, "model": "unknown", "status": "unknown", "detail": ""}


@router.get("/providers")
async def list_providers():
    """List all LLM providers with liveness status."""
    providers = [
        _check_provider_liveness("openai"),
        _check_provider_liveness("anthropic"),
        _check_provider_liveness("ollama"),
    ]
    overall = "ok"
    ok_count = sum(1 for p in providers if p["status"] == "ok")
    if ok_count == 0:
        overall = "error"
    elif ok_count < len(providers):
        overall = "partial"

    return {
        "meta": _meta(),
        "status": overall,
        "providers": providers,
        "available_count": ok_count,
        "total_count": len(providers),
    }


@router.get("/roles")
async def list_agent_roles():
    """List all agent roles with capability details."""
    from mission.role_registry import ROLE_REGISTRY

    roles = []
    for key, role in ROLE_REGISTRY.items():
        roles.append({
            "id": key,
            "displayName": role.get("displayName", key),
            "defaultSkill": role.get("defaultSkill", ""),
            "allowedSkills": role.get("allowedSkills", []),
            "forbiddenSkills": role.get("forbiddenSkills", []),
            "toolPolicy": role.get("toolPolicy", ""),
            "allowedTools": role.get("allowedTools") or [],
            "toolCount": len(role.get("allowedTools") or []),
            "defaultModelTier": role.get("defaultModelTier", 0),
            "preferredModel": role.get("preferredModel", ""),
            "discoveryRights": role.get("discoveryRights", ""),
            "maxFileReads": role.get("maxFileReads", 0),
            "maxDirectoryReads": role.get("maxDirectoryReads", 0),
            "canExpand": role.get("canExpand", False),
        })

    return {
        "meta": _meta(),
        "total": len(roles),
        "roles": roles,
    }


@router.get("/capability-matrix")
async def capability_matrix():
    """Role-provider capability matrix showing which role uses which provider."""
    from mission.role_registry import ROLE_REGISTRY

    matrix = []
    for key, role in ROLE_REGISTRY.items():
        preferred = role.get("preferredModel", "")
        tier = role.get("defaultModelTier", 0)
        matrix.append({
            "role": key,
            "displayName": role.get("displayName", key),
            "preferredModel": preferred,
            "modelTier": tier,
            "toolPolicy": role.get("toolPolicy", ""),
            "toolCount": len(role.get("allowedTools") or []),
            "canExpand": role.get("canExpand", False),
            "discoveryRights": role.get("discoveryRights", ""),
        })

    return {
        "meta": _meta(),
        "matrix": matrix,
    }


@router.get("/performance")
async def agent_performance():
    """Per-role performance metrics from mission history (file-based)."""
    import glob
    from pathlib import Path

    missions_dir = Path(__file__).resolve().parent.parent.parent / "logs" / "missions"
    pattern = str(missions_dir / "mission-*.json")

    role_stats: dict[str, dict] = {}
    mission_roles: dict[str, set] = {}  # mid -> set of roles

    # Prefer summary files for richer stage data (role, toolCalls, durationMs, isRework)
    summary_pattern = str(missions_dir / "mission-*-summary.json")
    for fpath in glob.glob(summary_pattern):
        try:
            data = json.loads(Path(fpath).read_text(encoding="utf-8"))
            mid = data.get("missionId", os.path.basename(fpath).replace("-summary.json", ""))
            stages = data.get("stages", [])
            if not isinstance(stages, list):
                continue
            for s in stages:
                if not isinstance(s, dict):
                    continue
                role = s.get("role", s.get("specialist", "unknown"))
                if role not in role_stats:
                    role_stats[role] = {
                        "missions": 0,
                        "stages": 0,
                        "tool_calls": 0,
                        "reworks": 0,
                        "total_duration_ms": 0,
                    }
                role_stats[role]["stages"] += 1
                role_stats[role]["tool_calls"] += s.get("toolCalls", s.get("tool_call_count", 0)) or 0
                if s.get("isRework") or s.get("is_rework"):
                    role_stats[role]["reworks"] += 1
                dur = s.get("durationMs", s.get("duration_ms", 0)) or 0
                role_stats[role]["total_duration_ms"] += dur

                if mid not in mission_roles:
                    mission_roles[mid] = set()
                mission_roles[mid].add(role)
        except Exception:
            continue

    # Count missions per role
    for mid, roles in mission_roles.items():
        for role in roles:
            if role in role_stats:
                role_stats[role]["missions"] += 1

    performance = []
    for role, stats in sorted(role_stats.items()):
        avg_duration = (
            round(stats["total_duration_ms"] / stats["stages"])
            if stats["stages"] > 0 else 0
        )
        performance.append({
            "role": role,
            "missions": stats["missions"],
            "stages": stats["stages"],
            "tool_calls": stats["tool_calls"],
            "reworks": stats["reworks"],
            "avg_stage_duration_ms": avg_duration,
            "rework_rate": (
                round(stats["reworks"] / stats["stages"] * 100, 1)
                if stats["stages"] > 0 else 0
            ),
        })

    return {
        "meta": _meta(),
        "performance": performance,
    }
