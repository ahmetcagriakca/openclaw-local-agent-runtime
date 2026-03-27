"""Alert Notifier — Sprint 16: Telegram + log notification dispatch.

Task 16.7: Sends critical alerts to operator via Telegram.
"""
from __future__ import annotations

import logging
import os
import requests
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from observability.alert_engine import Alert

logger = logging.getLogger("mcc.observability.notifier")

SEVERITY_ICONS = {
    "critical": "\u2757",  # ❗
    "warning": "\u26a0\ufe0f",   # ⚠️
    "info": "\u2139\ufe0f",      # ℹ️
}


class AlertNotifier:
    """Dispatches alert notifications to Telegram and log."""

    def __init__(
        self,
        bot_token: str | None = None,
        chat_id: str | None = None,
    ):
        self._bot_token = bot_token or os.environ.get("OC_TELEGRAM_BOT_TOKEN", "")
        self._chat_id = chat_id or os.environ.get("OC_TELEGRAM_CHAT_ID", "")
        self._sent_count = 0

    def send_alert(self, alert: "Alert") -> bool:
        """Send alert notification to Telegram."""
        if not self._bot_token or not self._chat_id:
            logger.debug("Telegram not configured, skipping alert notification")
            return False

        icon = SEVERITY_ICONS.get(alert.severity, "\u2139\ufe0f")
        text = self._format_message(alert, icon)

        try:
            url = f"https://api.telegram.org/bot{self._bot_token}/sendMessage"
            resp = requests.post(url, json={
                "chat_id": self._chat_id,
                "text": text,
                "parse_mode": "Markdown",
            }, timeout=10)

            if resp.status_code == 200:
                self._sent_count += 1
                logger.info("Alert sent to Telegram: %s", alert.rule_id)
                return True
            else:
                # Retry without Markdown
                resp2 = requests.post(url, json={
                    "chat_id": self._chat_id,
                    "text": text.replace("*", "").replace("`", ""),
                }, timeout=10)
                if resp2.status_code == 200:
                    self._sent_count += 1
                    return True
                logger.warning("Telegram send failed: %s", resp2.text)
                return False
        except Exception as e:
            logger.error("Telegram notification error: %s", e)
            return False

    def _format_message(self, alert: "Alert", icon: str) -> str:
        """Format alert for Telegram."""
        details = alert.details
        lines = [
            f"{icon} *VEZIR ALERT — {alert.rule_id} {alert.rule_name}*",
            "",
            f"Mission: `{alert.mission_id}`",
            f"Severity: {alert.severity.upper()}",
            f"Event: {details.get('event_type', '')}",
        ]

        # Add relevant details
        if details.get("trigger_value"):
            lines.append(f"Trigger: {details['trigger_value']} (limit: {details.get('threshold', '?')})")
        if details.get("stage"):
            lines.append(f"Stage: {details['stage']}")
        if details.get("tool"):
            lines.append(f"Tool: {details['tool']}")
        if details.get("tokens") or details.get("total_consumed"):
            tokens = details.get("tokens", details.get("total_consumed", 0))
            lines.append(f"Tokens: {tokens:,}")

        return "\n".join(lines)

    @property
    def sent_count(self) -> int:
        return self._sent_count
