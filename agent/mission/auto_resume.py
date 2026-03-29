"""Auto-resume — scan and resume incomplete missions from persisted state.

B-106: On runner startup (--auto-resume), scans logs/missions/ for
incomplete mission files and resumes them via retry_from_mission.
Also supports resuming a single mission by ID (--resume MISSION_ID).
"""
import json
import logging
import os
from pathlib import Path

logger = logging.getLogger("mcc.mission.auto_resume")

MISSIONS_DIR = Path(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
) / "logs" / "missions"

# Statuses that indicate an incomplete/failed mission eligible for resume
RESUMABLE_STATUSES = {"failed", "running", "executing"}

# Suffixes for non-canonical mission files (state, summary, etc.)
_EXCLUDED_SUFFIXES = ("-state.json", "-summary.json", "-token-report.json")


def _is_canonical_mission_file(path: Path) -> bool:
    """Check if a file is a canonical mission file (not state/summary/report)."""
    name = path.name
    return not any(name.endswith(suffix) for suffix in _EXCLUDED_SUFFIXES)


def find_incomplete_missions() -> list[dict]:
    """Scan missions directory for incomplete mission files.

    Returns list of mission dicts that are resumable.
    """
    if not MISSIONS_DIR.exists():
        return []

    incomplete = []
    seen_ids: set[str] = set()
    for f in MISSIONS_DIR.glob("mission-*.json"):
        # Skip non-canonical files (state, summary, token-report)
        if not _is_canonical_mission_file(f):
            continue
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            mission_id = data.get("missionId", "")
            status = data.get("status", "")
            if status in RESUMABLE_STATUSES:
                # Must have at least one stage to be resumable
                # Dedup: only one entry per mission ID
                if data.get("stages") and mission_id not in seen_ids:
                    incomplete.append(data)
                    seen_ids.add(mission_id)
        except (json.JSONDecodeError, OSError) as e:
            logger.warning("Could not read mission file %s: %s", f, e)

    # Sort by startedAt descending (newest first)
    incomplete.sort(
        key=lambda m: m.get("startedAt", ""), reverse=True)
    return incomplete


def resume_mission(mission_id: str, *, agent_id: str = "gpt-general",
                   user_id: str = "auto-resume",
                   session_id: str = "") -> dict:
    """Resume a specific mission by its ID.

    Loads mission file from disk and passes it as retry_from_mission
    to MissionController.execute_mission().
    """
    from mission.controller import MissionController

    mission_path = MISSIONS_DIR / f"{mission_id}.json"
    if not mission_path.exists():
        return {"status": "error",
                "error": f"Mission file not found: {mission_id}"}

    try:
        mission_data = json.loads(mission_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as e:
        return {"status": "error",
                "error": f"Could not read mission: {e}"}

    status = mission_data.get("status", "")
    if status not in RESUMABLE_STATUSES:
        return {"status": "error",
                "error": f"Mission not resumable (status={status})"}

    if not session_id:
        import time
        session_id = f"resume-{int(time.time())}-{os.getpid()}"

    logger.info("Resuming mission %s (status=%s)", mission_id, status)

    controller = MissionController(planner_agent_id=agent_id)
    result = controller.execute_mission(
        goal=mission_data.get("goal", ""),
        user_id=user_id,
        session_id=session_id,
        retry_from_mission=mission_data,
    )

    return {
        "original_mission_id": mission_id,
        "new_mission_id": result.get("missionId"),
        "status": result.get("status"),
        "summary": result.get("summary", ""),
    }


def scan_and_resume(*, agent_id: str = "gpt-general",
                    user_id: str = "auto-resume",
                    max_missions: int = 5) -> dict:
    """Scan for all incomplete missions and resume them.

    Returns summary of resume attempts.
    """
    incomplete = find_incomplete_missions()

    if not incomplete:
        logger.info("No incomplete missions found")
        return {"scanned": True, "found": 0, "resumed": []}

    logger.info("Found %d incomplete missions", len(incomplete))

    # Limit to max_missions to avoid overload
    to_resume = incomplete[:max_missions]
    results = []

    for mission_data in to_resume:
        mission_id = mission_data.get("missionId", "")
        try:
            result = resume_mission(
                mission_id, agent_id=agent_id, user_id=user_id)
            results.append(result)
        except Exception as e:
            logger.error("Failed to resume %s: %s", mission_id, e)
            results.append({
                "original_mission_id": mission_id,
                "status": "error",
                "error": str(e),
            })

    return {
        "scanned": True,
        "found": len(incomplete),
        "resumed": results,
    }
