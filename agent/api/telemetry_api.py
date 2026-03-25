"""Telemetry API — GPT Fix 3: wrapper response. Fix 8: missionId filter."""
from typing import Optional

from fastapi import APIRouter

from api.schemas import TelemetryResponse

router = APIRouter(tags=["telemetry"])


@router.get("/telemetry", response_model=TelemetryResponse)
async def list_telemetry(mission_id: Optional[str] = None,
                         limit: int = 200):
    from api.server import normalizer
    events, meta = normalizer.get_telemetry(
        mission_id=mission_id, limit=limit)
    return TelemetryResponse(meta=meta, events=events)
