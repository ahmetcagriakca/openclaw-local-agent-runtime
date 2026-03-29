"""Mutation Bridge — Sprint 11 Task 11.4.

Atomic request artifact writer. API mutation endpoints call this to write
signal artifacts that the runtime/controller consumes.

Single rule (D-001, D-062, D-063):
  API only writes atomic request artifact; runtime/controller remains sole executor.

Signal artifact format (SPRINT-11-TASK-BREAKDOWN.md Section 3):
  {
    "requestId": "req-uuid",
    "type": "approve|reject|cancel|retry",
    "targetId": "approval-id or mission-id",
    "missionId": "mission-id",
    "requestedAt": "ISO-8601",
    "source": "dashboard",
    "operatorInfo": { "tabId": "...", "sessionId": "..." }
  }

Artifact path: logs/missions/{missionId}/{type}-request-{uuid}.json
"""
import logging
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from utils.atomic_write import atomic_write_json

logger = logging.getLogger("mcc.mutation.bridge")

# Pattern for valid mission/target IDs — prevents path traversal.
_SAFE_ID_RE = re.compile(r"^[a-zA-Z0-9_-]+$")


def write_signal_artifact(
    *,
    missions_dir: Path,
    mutation_type: str,
    target_id: str,
    mission_id: str,
    tab_id: str = "",
    session_id: str = "",
) -> tuple[str, str, Path]:
    """Write an atomic signal artifact for a mutation request.

    Args:
        missions_dir: Base missions directory (logs/missions/).
        mutation_type: approve | reject | cancel | retry.
        target_id: Approval ID or mission ID being mutated.
        mission_id: Mission ID (directory for artifact).
        tab_id: Browser tab ID from X-Tab-Id header.
        session_id: Browser session ID from X-Session-Id header.

    Returns:
        Tuple of (requestId, requestedAt ISO string, artifact Path).

    Raises:
        OSError: If directory creation or file write fails.
    """
    # Validate mission_id to prevent path traversal
    if not _SAFE_ID_RE.match(mission_id):
        raise ValueError(f"Invalid mission_id format: {mission_id}")
    if not _SAFE_ID_RE.match(target_id):
        raise ValueError(f"Invalid target_id format: {target_id}")

    request_id = f"req-{uuid.uuid4()}"
    requested_at = datetime.now(timezone.utc).isoformat()

    artifact = {
        "requestId": request_id,
        "type": mutation_type,
        "targetId": target_id,
        "missionId": mission_id,
        "requestedAt": requested_at,
        "source": "dashboard",
        "operatorInfo": {
            "tabId": tab_id,
            "sessionId": session_id,
        },
    }

    mission_dir = missions_dir / mission_id
    mission_dir.mkdir(parents=True, exist_ok=True)
    artifact_path = mission_dir / f"{mutation_type}-request-{request_id}.json"

    atomic_write_json(artifact_path, artifact)
    logger.info(
        "Signal artifact written: type=%s target=%s requestId=%s path=%s",
        mutation_type, target_id, request_id, artifact_path,
    )

    return request_id, requested_at, artifact_path


def has_pending_signal(
    missions_dir: Path,
    mission_id: str,
    mutation_type: str,
    target_id: str,
) -> Optional[str]:
    """Check if a pending signal artifact exists for the same target+type.

    Returns the existing requestId if found, None otherwise.
    Used to prevent duplicate mutations (Test 5: 409 conflict).
    Signal artifacts older than 60 seconds are considered expired and cleaned up.
    """
    import json
    import time

    # Validate mission_id to prevent path traversal
    if not _SAFE_ID_RE.match(mission_id):
        return None

    SIGNAL_TTL_S = 60  # Expire signals after 60 seconds

    mission_dir = missions_dir / mission_id
    if not mission_dir.exists():
        return None

    pattern = f"{mutation_type}-request-req-*.json"
    for artifact_path in mission_dir.glob(pattern):
        try:
            # Expire old artifacts — controller may not be running
            age_s = time.time() - artifact_path.stat().st_mtime
            if age_s > SIGNAL_TTL_S:
                try:
                    artifact_path.unlink()
                    logger.info("Expired signal artifact deleted: %s (age=%ds)", artifact_path.name, int(age_s))
                except OSError as oe:
                    logger.warning("Failed to delete expired artifact %s: %s", artifact_path.name, oe)
                # Skip this artifact regardless of whether delete succeeded
                continue

            data = json.loads(artifact_path.read_text(encoding="utf-8"))
            if data.get("targetId") == target_id:
                return data.get("requestId")
        except Exception:
            continue

    return None
