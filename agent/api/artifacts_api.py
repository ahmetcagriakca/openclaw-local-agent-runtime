"""Artifacts API — B-016 Task Result Artifact Access (Sprint 51).

Endpoints for listing and accessing mission task artifacts.
Reads from mission JSON files in logs/missions/.
"""
import json
import logging
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(tags=["artifacts"])
logger = logging.getLogger("mcc.api.artifacts")

# Paths
OC_ROOT = Path(__file__).resolve().parent.parent.parent
MISSIONS_DIR = OC_ROOT / "logs" / "missions"


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "mission_files", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


def _load_mission(mission_id: str) -> dict | None:
    """Load a mission JSON file by ID."""
    for f in MISSIONS_DIR.glob("*.json"):
        if f.stem.endswith("-token-report"):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("missionId") == mission_id:
                return data
        except (json.JSONDecodeError, OSError):
            continue
    return None


def _extract_artifacts(mission: dict) -> list[dict]:
    """Extract all artifacts from mission stages."""
    artifacts = []
    for i, stage in enumerate(mission.get("stages", [])):
        stage_id = stage.get("stage_id", f"stage-{i}")
        specialist = stage.get("specialist", "unknown")
        stage_artifacts = stage.get("artifacts", [])

        # Stage result as artifact
        result = stage.get("result", "")
        if result:
            artifact = {
                "id": f"{stage_id}-result",
                "type": "stage_result",
                "stage_id": stage_id,
                "role": specialist,
                "size": len(result.encode("utf-8")) if isinstance(result, str) else 0,
                "created_at": stage.get("finished_at", ""),
                "preview": result[:200] if isinstance(result, str) else "",
            }
            artifacts.append(artifact)

        # Raw artifacts from stage
        for j, raw in enumerate(stage_artifacts):
            artifact = {
                "id": f"{stage_id}-artifact-{j}",
                "type": "raw_artifact",
                "stage_id": stage_id,
                "role": specialist,
                "size": len(json.dumps(raw).encode("utf-8")) if raw else 0,
                "created_at": stage.get("finished_at", ""),
                "data": raw,
            }
            artifacts.append(artifact)

    # Top-level artifacts
    for k, top_artifact in enumerate(mission.get("artifacts", [])):
        artifact = {
            "id": f"mission-artifact-{k}",
            "type": "mission_artifact",
            "stage_id": "",
            "role": "",
            "size": len(json.dumps(top_artifact).encode("utf-8")) if top_artifact else 0,
            "created_at": mission.get("finishedAt", ""),
            "data": top_artifact,
        }
        artifacts.append(artifact)

    return artifacts


@router.get("/missions/{mission_id}/artifacts")
async def list_artifacts(mission_id: str):
    """List all artifacts for a mission."""
    mission = _load_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission not found: {mission_id}")

    artifacts = _extract_artifacts(mission)

    # Return without full data for listing (summary only)
    summaries = []
    for a in artifacts:
        summary = {
            "id": a["id"],
            "type": a["type"],
            "stage_id": a["stage_id"],
            "role": a["role"],
            "size": a["size"],
            "created_at": a["created_at"],
        }
        if "preview" in a:
            summary["preview"] = a["preview"]
        summaries.append(summary)

    return {
        "meta": _meta(),
        "mission_id": mission_id,
        "artifacts": summaries,
        "count": len(summaries),
    }


@router.get("/missions/{mission_id}/artifacts/{artifact_id}")
async def get_artifact(mission_id: str, artifact_id: str):
    """Get a specific artifact by ID with full content."""
    mission = _load_mission(mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission not found: {mission_id}")

    artifacts = _extract_artifacts(mission)
    for a in artifacts:
        if a["id"] == artifact_id:
            return {
                "meta": _meta(),
                "artifact": a,
            }

    raise HTTPException(
        status_code=404,
        detail=f"Artifact not found: {artifact_id} in mission {mission_id}"
    )
