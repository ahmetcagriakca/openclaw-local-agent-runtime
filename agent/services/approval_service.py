"""Telegram-based approval service for high-risk tool calls."""
import json
import os
import time
import subprocess
from datetime import datetime, timezone

APPROVALS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
    "logs", "approvals"
)


class ApprovalService:
    def __init__(self, timeout_seconds=60):
        self.timeout = timeout_seconds
        os.makedirs(APPROVALS_DIR, exist_ok=True)

        # Resolve Telegram bot token
        self.bot_token = os.environ.get("OC_TELEGRAM_BOT_TOKEN")
        if not self.bot_token:
            self._resolve_token_from_wsl()

        self.chat_id = os.environ.get("OC_TELEGRAM_CHAT_ID", "8654710624")

    def _resolve_token_from_wsl(self):
        """Try to read bot token from WSL OpenClaw .env file."""
        try:
            result = subprocess.run(
                ["wsl", "-d", "Ubuntu-E", "--", "bash", "-c",
                 "grep '^TELEGRAM_BOT_TOKEN=' /home/akca/.openclaw/.env 2>/dev/null"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0 and "=" in result.stdout:
                self.bot_token = result.stdout.strip().split("=", 1)[1].strip()
        except Exception:
            pass

    def request_approval(self, tool_name: str, tool_params: dict,
                         risk: str, powershell_command: str,
                         session_id: str) -> dict:
        """Request approval for a high-risk tool call.

        Returns: {
            "approved": bool,
            "approvalId": str,
            "method": "telegram_reply"|"timeout"|"no_token",
            "respondedAt": str|None
        }
        """
        # Generate approval ID
        ts = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        apv_id = f"apv-{ts}-{os.getpid()}"

        # Build approval record
        record = {
            "approvalId": apv_id,
            "sessionId": session_id,
            "toolName": tool_name,
            "toolParams": tool_params,
            "risk": risk,
            "command": powershell_command[:200] if powershell_command else "",
            "requestedAt": datetime.now(timezone.utc).isoformat(),
            "expiresAt": None,
            "status": "pending",
            "decision": None,
            "decidedAt": None
        }

        # Save approval record
        record_path = os.path.join(APPROVALS_DIR, f"{apv_id}.json")
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # If no bot token, can't send Telegram — auto-deny
        if not self.bot_token:
            record["status"] = "denied"
            record["decision"] = "no_token"
            record["decidedAt"] = datetime.now(timezone.utc).isoformat()
            with open(record_path, "w", encoding="utf-8") as f:
                json.dump(record, f, ensure_ascii=False, indent=2)
            return {
                "approved": False,
                "approvalId": apv_id,
                "method": "no_token",
                "respondedAt": None
            }

        # Send Telegram approval request
        risk_emoji = {"high": "\u26a0\ufe0f", "critical": "\U0001f534"}.get(risk, "\u26a0\ufe0f")
        message = (
            f"{risk_emoji} <b>Agent Approval Request</b> [{apv_id}]\n\n"
            f"Tool: <code>{tool_name}</code>\n"
            f"Parameters: <code>{json.dumps(tool_params, ensure_ascii=False)}</code>\n"
            f"Risk: <b>{risk.upper()}</b>\n"
            f"Command preview: <code>{(powershell_command or '')[:100]}</code>\n\n"
            f"Reply: <code>approve {apv_id}</code> or <code>deny {apv_id}</code>\n"
            f"Auto-deny in {self.timeout} seconds."
        )

        # Get last update_id before sending (to only check new messages)
        last_update_id = self._get_last_update_id()

        self._send_telegram(message)

        # Poll for response
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            time.sleep(3)  # Check every 3 seconds

            reply = self._check_for_reply(apv_id, last_update_id)
            if reply is not None:
                approved = reply == "approve"
                record["status"] = "approved" if approved else "denied"
                record["decision"] = reply
                record["decidedAt"] = datetime.now(timezone.utc).isoformat()
                with open(record_path, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False, indent=2)

                # Send confirmation
                result_emoji = "\u2705" if approved else "\u274c"
                self._send_telegram(f"{result_emoji} {apv_id}: {'Approved' if approved else 'Denied'}")

                return {
                    "approved": approved,
                    "approvalId": apv_id,
                    "method": "telegram_reply",
                    "respondedAt": record["decidedAt"]
                }

        # Timeout — auto-deny
        record["status"] = "denied"
        record["decision"] = "timeout"
        record["decidedAt"] = datetime.now(timezone.utc).isoformat()
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        self._send_telegram(f"\u23f0 {apv_id}: Auto-denied (timeout)")

        return {
            "approved": False,
            "approvalId": apv_id,
            "method": "timeout",
            "respondedAt": record["decidedAt"]
        }

    def _send_telegram(self, message: str):
        """Send a message via Telegram Bot API."""
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            requests.post(url, json={
                "chat_id": self.chat_id,
                "text": message,
                "parse_mode": "HTML"
            }, timeout=10)
        except Exception:
            pass  # Best effort

    def _get_last_update_id(self) -> int:
        """Get the latest update_id to only check newer messages."""
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            resp = requests.get(url, params={"limit": 1, "offset": -1}, timeout=10)
            data = resp.json()
            if data.get("ok") and data.get("result"):
                return data["result"][-1]["update_id"]
        except Exception:
            pass
        return 0

    def _check_for_reply(self, apv_id: str, after_update_id: int) -> str | None:
        """Check Telegram for approve/deny reply.

        Returns: "approve" | "deny" | None
        """
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            resp = requests.get(url, params={
                "offset": after_update_id + 1,
                "timeout": 1
            }, timeout=5)
            data = resp.json()

            if not data.get("ok"):
                return None

            for update in data.get("result", []):
                msg = update.get("message", {})
                text = (msg.get("text") or "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                # Only check messages from the right chat
                if chat_id != str(self.chat_id):
                    continue

                # Check for approve/deny with approval ID
                apv_lower = apv_id.lower()
                if f"approve {apv_lower}" in text or f"yes {apv_lower}" in text:
                    return "approve"
                if f"deny {apv_lower}" in text or f"no {apv_lower}" in text:
                    return "deny"

                # Also accept simple "yes"/"no" if it's the most recent message
                # (user convenience — only if single pending approval)
                if text in ("yes", "evet", "approve", "onayla"):
                    return "approve"
                if text in ("no", "hayir", "deny", "reddet"):
                    return "deny"

            return None
        except Exception:
            return None
