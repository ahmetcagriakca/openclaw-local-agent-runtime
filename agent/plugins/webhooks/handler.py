"""Webhook notifications handler — D-118 reference plugin.

Sends HTTP POST to configured webhook URL on mission events.
Compatible with Slack incoming webhooks and Discord webhooks.
"""
import json
import logging
from urllib.request import Request, urlopen
from urllib.error import URLError

logger = logging.getLogger("mcc.plugins.webhooks")

_config = {}


def init(config: dict) -> None:
    """Initialize webhook plugin with config."""
    global _config
    _config = config
    url = config.get("webhook_url", "")
    logger.info("Webhook plugin initialized. URL: %s...", url[:50] if url else "(not set)")


def _send_webhook(payload: dict) -> dict:
    """Send payload to configured webhook URL."""
    url = _config.get("webhook_url")
    if not url:
        logger.warning("Webhook URL not configured, skipping")
        return {"sent": False, "reason": "no_url"}

    try:
        data = json.dumps(payload).encode("utf-8")
        req = Request(url, data=data, headers={"Content-Type": "application/json"})
        with urlopen(req, timeout=10) as resp:
            status = resp.status
            logger.info("Webhook sent: %d", status)
            return {"sent": True, "status": status}
    except URLError as e:
        logger.error("Webhook failed: %s", e)
        return {"sent": False, "error": str(e)}
    except Exception as e:
        logger.error("Webhook unexpected error: %s", e)
        return {"sent": False, "error": str(e)}


def on_mission_completed(event_data: dict) -> dict:
    """Handle mission_completed event."""
    mission_id = event_data.get("missionId", "unknown")
    goal = event_data.get("goal", "")
    payload = {
        "text": f"Mission completed: {mission_id}\nGoal: {goal}",
        "username": "Vezir",
    }
    return _send_webhook(payload)


def on_mission_failed(event_data: dict) -> dict:
    """Handle mission_failed event."""
    mission_id = event_data.get("missionId", "unknown")
    error = event_data.get("error", "unknown error")
    payload = {
        "text": f"Mission FAILED: {mission_id}\nError: {error}",
        "username": "Vezir",
    }
    return _send_webhook(payload)


def on_approval_requested(event_data: dict) -> dict:
    """Handle approval_requested event."""
    approval_id = event_data.get("approvalId", "unknown")
    tool = event_data.get("toolName", "unknown")
    risk = event_data.get("risk", "unknown")
    payload = {
        "text": f"Approval needed: {approval_id}\nTool: {tool} (risk: {risk})",
        "username": "Vezir",
    }
    return _send_webhook(payload)
