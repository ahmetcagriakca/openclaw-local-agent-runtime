"""Replay API — B-111 (Sprint 52).

Endpoints for mission replay and fixture generation.
"""
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException

router = APIRouter(prefix="/missions", tags=["missions"])
logger = logging.getLogger("mcc.api.replay")

OC_ROOT = Path(__file__).resolve().parent.parent.parent
MISSIONS_DIR = OC_ROOT / "logs" / "missions"

sys.path.insert(0, str(OC_ROOT / "tools"))


def _meta() -> dict:
    return {
        "freshnessMs": 0,
        "dataQuality": "fresh",
        "sourcesUsed": [{"name": "replay_engine", "ageMs": 0, "status": "fresh"}],
        "sourcesMissing": [],
        "generatedAt": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/replay/list")
async def list_replayable(limit: int = 20):
    """List missions available for replay."""
    from replay import list_completed_missions
    missions = list_completed_missions(MISSIONS_DIR, limit=limit)
    return {
        "meta": _meta(),
        "missions": missions,
        "count": len(missions),
    }


@router.get("/replay/{mission_id}")
async def replay_mission(mission_id: str):
    """Dry-run replay a mission and return validation report."""
    from replay import load_mission
    from replay import replay_mission as do_replay
    data = load_mission(mission_id, MISSIONS_DIR)
    if not data:
        raise HTTPException(status_code=404,
                            detail=f"Mission not found: {mission_id}")
    report = do_replay(data)
    return {
        "meta": _meta(),
        "report": report,
    }


@router.get("/replay/{mission_id}/fixture")
async def generate_fixture(mission_id: str):
    """Generate a test fixture from a completed mission."""
    from replay import generate_fixture as do_fixture
    from replay import load_mission
    data = load_mission(mission_id, MISSIONS_DIR)
    if not data:
        raise HTTPException(status_code=404,
                            detail=f"Mission not found: {mission_id}")
    fixture = do_fixture(data)
    return {
        "meta": _meta(),
        "fixture": fixture,
    }
