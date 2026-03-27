"""Mission API endpoints — read-only (D-059). GPT Fix 3: wrapper responses."""
import json
import os

from fastapi import APIRouter, HTTPException

from api.schemas import (
    APIError,
    MissionDetailResponse,
    MissionListResponse,
    StageDetail,
    StageListResponse,
)

MISSIONS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "missions"
)

router = APIRouter(tags=["missions"])


@router.get("/missions", response_model=MissionListResponse)
async def list_missions():
    from api.server import normalizer
    missions, meta = normalizer.list_missions()
    return MissionListResponse(meta=meta, missions=missions)


@router.get("/missions/{mission_id}", response_model=MissionDetailResponse,
            responses={404: {"model": APIError}})
async def get_mission(mission_id: str):
    from api.server import normalizer
    result = normalizer.get_mission(mission_id)
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")
    mission, meta = result
    return MissionDetailResponse(meta=meta, mission=mission)


@router.get("/missions/{mission_id}/stages",
            response_model=StageListResponse)
async def get_mission_stages(mission_id: str):
    from api.server import normalizer
    result = normalizer.get_mission(mission_id)
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")
    mission, meta = result
    return StageListResponse(meta=meta, stages=mission.stages)


@router.get("/missions/{mission_id}/stages/{stage_idx}",
            response_model=StageDetail,
            responses={404: {"model": APIError}})
async def get_mission_stage(mission_id: str, stage_idx: int):
    from api.server import normalizer
    result = normalizer.get_mission(mission_id)
    if result is None:
        raise HTTPException(status_code=404,
                            detail=f"Mission {mission_id} not found")
    mission, _ = result
    if stage_idx < 0 or stage_idx >= len(mission.stages):
        raise HTTPException(status_code=404,
                            detail=f"Stage {stage_idx} not found")
    return mission.stages[stage_idx]


@router.get("/missions/{mission_id}/token-report",
            responses={404: {"model": APIError}})
async def get_token_report(mission_id: str):
    """Return the per-mission token usage report (D-102).

    Resolves dashboard placeholder IDs to controller mission IDs
    so the correct token-report.json file is found.
    """
    from api.server import normalizer
    file_id = normalizer.resolve_file_id(mission_id)
    report_path = os.path.join(
        MISSIONS_DIR, f"{file_id}-token-report.json")
    if not os.path.isfile(report_path):
        raise HTTPException(status_code=404,
                            detail=f"Token report for {mission_id} not found")
    with open(report_path, "r", encoding="utf-8") as f:
        return json.load(f)
