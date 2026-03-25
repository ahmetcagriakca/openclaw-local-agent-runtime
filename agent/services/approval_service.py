"""Telegram-based approval service for high-risk tool calls.

SUNSET NOTICE (D-063):
    This strict-ID-based implementation is valid until Phase 5C (Sprint 11).
    Per decision D-063, the approval mechanism will migrate to a service layer
    with structured request/response contracts. Do not extend this module with
    new approval patterns — design them for the future service layer instead.

Approval flow:
1. Write pending approval to logs/approvals/apv-XXX.json
2. Send one-way Telegram notification via Bot API sendMessage
3. Poll the approval file for status change (set by oc-approve CLI tool)
4. Timeout after N seconds -> auto-deny

The user approves by running: oc-approve apv-XXX
Or from Telegram via OpenClaw: "approve apv-XXX"
"""
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
            "method": "file_approval"|"timeout"|"no_token",
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
            "status": "pending",
            "decision": None,
            "decidedAt": None
        }

        # Save approval record
        record_path = os.path.join(APPROVALS_DIR, f"{apv_id}.json")
        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)

        # Send Telegram notification (one-way — no getUpdates polling)
        if self.bot_token:
            risk_emoji = {"high": "\u26a0\ufe0f", "critical": "\U0001f534"}.get(risk, "\u26a0\ufe0f")
            message = (
                f"{risk_emoji} <b>Agent Approval Request</b>\n"
                f"ID: <code>{apv_id}</code>\n\n"
                f"Tool: <code>{tool_name}</code>\n"
                f"Parameters: <code>{json.dumps(tool_params, ensure_ascii=False)}</code>\n"
                f"Risk: <b>{risk.upper()}</b>\n\n"
                f"\u2705 Approve: <code>approve {apv_id}</code>\n"
                f"\u274c Deny: <code>deny {apv_id}</code>\n\n"
                f"Auto-deny in {self.timeout} seconds."
            )
            self._send_telegram(message)
        else:
            # No bot token — auto-deny
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

        # Record the send timestamp to only check newer Telegram messages
        send_time = int(time.time())

        # Poll: check both file changes AND Telegram replies
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            time.sleep(3)  # Check every 3 seconds

            # Check 1: file-based approval (from oc-approve CLI)
            try:
                with open(record_path, "r", encoding="utf-8") as f:
                    current = json.load(f)

                if current.get("status") in ("approved", "denied"):
                    approved = current["status"] == "approved"

                    result_emoji = "\u2705" if approved else "\u274c"
                    self._send_telegram(f"{result_emoji} {apv_id}: {'Approved' if approved else 'Denied'}")

                    return {
                        "approved": approved,
                        "approvalId": apv_id,
                        "method": "file_approval",
                        "respondedAt": current.get("decidedAt")
                    }
            except Exception:
                pass

            # Check 2: Telegram reply (peek without consuming — no offset)
            if self.bot_token:
                reply = self._peek_telegram_reply(apv_id, send_time)
                if reply is not None:
                    approved = reply == "approve"
                    record["status"] = "approved" if approved else "denied"
                    record["decision"] = f"telegram_{reply}"
                    record["decidedAt"] = datetime.now(timezone.utc).isoformat()
                    with open(record_path, "w", encoding="utf-8") as f:
                        json.dump(record, f, ensure_ascii=False, indent=2)

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

    def _peek_telegram_reply(self, apv_id: str, after_unix: int) -> str | None:
        """Peek at recent Telegram messages for approve/deny reply.

        STRICT MODE (6D):
        - "approve <id>" or "deny <id>" -> always accepted
        - Simple "yes"/"no" -> only if exactly 1 pending approval
          (backward compat with deprecation warning)
        - Multiple pending + "yes" -> rejected (returns None)

        Returns: "approve" | "deny" | None
        """
        try:
            import requests
            url = f"https://api.telegram.org/bot{self.bot_token}/getUpdates"
            resp = requests.get(url, params={"limit": 20, "timeout": 0}, timeout=5)
            data = resp.json()

            if not data.get("ok"):
                return None

            # Count current pending approvals
            pending_count = self._count_pending_approvals()

            for update in data.get("result", []):
                msg = update.get("message", {})
                msg_date = msg.get("date", 0)

                if msg_date < after_unix:
                    continue

                text = (msg.get("text") or "").strip().lower()
                chat_id = str(msg.get("chat", {}).get("id", ""))

                if chat_id != str(self.chat_id):
                    continue

                apv_lower = apv_id.lower()

                # STRICT: ID-based approve/deny (always accepted)
                if f"approve {apv_lower}" in text or f"yes {apv_lower}" in text:
                    return "approve"
                if f"deny {apv_lower}" in text or f"no {apv_lower}" in text:
                    return "deny"

                # BACKWARD COMPAT: Simple yes/no
                if text in ("yes", "evet", "approve", "onayla"):
                    if pending_count <= 1:
                        self._send_telegram(
                            f"\u26a0\ufe0f DEPRECATION: Plain '{text}' accepted for {apv_id}. "
                            f"Please use 'approve {apv_id}' format in the future."
                        )
                        return "approve"
                    else:
                        self._send_telegram(
                            f"\u274c Ambiguous: {pending_count} pending approvals. "
                            f"Please specify: 'approve {apv_id}' or 'deny {apv_id}'"
                        )
                        return None

                if text in ("no", "hayir", "hayır", "deny", "reddet"):
                    if pending_count <= 1:
                        self._send_telegram(
                            f"\u26a0\ufe0f DEPRECATION: Plain '{text}' accepted for {apv_id}. "
                            f"Please use 'deny {apv_id}' format in the future."
                        )
                        return "deny"
                    else:
                        self._send_telegram(
                            f"\u274c Ambiguous: {pending_count} pending approvals. "
                            f"Please specify: 'approve {apv_id}' or 'deny {apv_id}'"
                        )
                        return None

            return None
        except Exception:
            return None

    def _count_pending_approvals(self) -> int:
        """Count current pending approval files."""
        import glob
        pattern = os.path.join(APPROVALS_DIR, "apv-*.json")
        count = 0
        for path in glob.glob(pattern):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    record = json.load(f)
                if record.get("status") == "pending":
                    count += 1
            except Exception:
                pass
        return count

    def _send_telegram(self, message: str):
        """Send a message via Telegram Bot API (one-way, no polling)."""
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


def approve(apv_id: str) -> bool:
    """Approve a pending approval request. Called by oc-approve CLI."""
    return _decide(apv_id, "approved")


def deny(apv_id: str) -> bool:
    """Deny a pending approval request. Called by oc-approve CLI."""
    return _decide(apv_id, "denied")


def _decide(apv_id: str, status: str) -> bool:
    """Update approval file with decision."""
    record_path = os.path.join(APPROVALS_DIR, f"{apv_id}.json")
    if not os.path.exists(record_path):
        return False

    try:
        with open(record_path, "r", encoding="utf-8") as f:
            record = json.load(f)

        if record.get("status") != "pending":
            return False  # Already decided

        record["status"] = status
        record["decision"] = status
        record["decidedAt"] = datetime.now(timezone.utc).isoformat()

        with open(record_path, "w", encoding="utf-8") as f:
            json.dump(record, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False
