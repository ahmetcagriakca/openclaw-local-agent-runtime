"""Approval expiration checker — D-121.

Periodic check for expired pending approvals.
Default timeout: 30 minutes.
"""
import json
import logging
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger("mcc.approval.expiry")

DEFAULT_TIMEOUT_MINUTES = 30


def check_expired_approvals(approvals_dir: Path, timeout_minutes: int = DEFAULT_TIMEOUT_MINUTES) -> list[str]:
    """Check for and expire timed-out approvals. Returns list of expired IDs."""
    expired = []
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=timeout_minutes)

    for f in approvals_dir.glob("*.json"):
        try:
            data = json.loads(f.read_text(encoding="utf-8"))
            if data.get("status") != "pending":
                continue

            created = data.get("created_at") or data.get("requestedAt", "")
            if not created:
                continue

            created_dt = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if created_dt < cutoff:
                data["status"] = "expired"
                data["expired_at"] = datetime.now(timezone.utc).isoformat()
                f.write_text(json.dumps(data, indent=2), encoding="utf-8")
                expired.append(data.get("approvalId", f.stem))
                logger.info("Approval expired: %s", data.get("approvalId"))
        except (json.JSONDecodeError, ValueError, OSError) as e:
            logger.warning("Error checking approval %s: %s", f, e)

    return expired
