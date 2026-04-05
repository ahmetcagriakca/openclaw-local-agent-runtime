"""Telegram Bot Poller — listens for messages and routes to Vezir.

Runs as a long-polling loop:
  - Normal messages → oc-agent-runner (single-turn)
  - /mission prefix → oc-agent-runner --mission (multi-stage pipeline)
  - /health → returns system health summary
  - /status → returns running missions

Usage:
  python telegram_bot.py
"""
import json
import logging
import os
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [TG-BOT] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("tg-bot")

# ── Config ──────────────────────────────────────────────────────
BOT_TOKEN = os.environ.get("OC_TELEGRAM_BOT_TOKEN")
CHAT_ID = os.environ.get("OC_TELEGRAM_CHAT_ID", "")
if not CHAT_ID:
    log.warning("OC_TELEGRAM_CHAT_ID not set — using hardcoded default. "
                 "Set env var in production.")
    CHAT_ID = "8654710624"
AGENT_SCRIPT = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "oc-agent-runner.py")
PYTHON_EXE = sys.executable
POLL_TIMEOUT = 30  # long-polling seconds
AGENT_TIMEOUT = 300  # max agent execution seconds

# Token resolution sources (tried in order)
_TOKEN_SOURCES = [
    # 1. Direct env var
    lambda: os.environ.get("OC_TELEGRAM_BOT_TOKEN"),
    # 2. .env file in agent directory
    lambda: _read_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env"),
                           "OC_TELEGRAM_BOT_TOKEN"),
    # 3. .env file in project root
    lambda: _read_env_file(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"),
                           "OC_TELEGRAM_BOT_TOKEN"),
    # 4. Legacy: TELEGRAM_BOT_TOKEN env var
    lambda: os.environ.get("TELEGRAM_BOT_TOKEN"),
    # 5. WSL fallback
    lambda: _read_wsl_token(),
]


def _read_env_file(path: str, key: str):
    """Read a key from a .env file."""
    try:
        path = os.path.abspath(path)
        if not os.path.isfile(path):
            return None
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith(f"{key}="):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
    except Exception:
        return None
    return None


def _read_wsl_token():
    """Legacy WSL token fallback removed (D-137 bridge contract).

    Token must be set via OC_TELEGRAM_BOT_TOKEN env var.
    Direct WSL subprocess calls are not permitted outside the canonical bridge.
    """
    return None


def _resolve_token():
    """Resolve bot token from multiple sources."""
    global BOT_TOKEN
    if BOT_TOKEN:
        return
    for source in _TOKEN_SOURCES:
        try:
            token = source()
            if token:
                BOT_TOKEN = token
                log.info("Bot token resolved from %s", source.__name__ if hasattr(source, '__name__') else 'source')
                return
        except Exception:
            continue
    log.error("Bot token could not be resolved from any source.")


def tg_api(method: str, params: dict = None) -> dict:
    """Call Telegram Bot API."""
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN not set — cannot call Telegram API")
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    if params:
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(url, data=data,
                                     headers={"Content-Type": "application/json"})
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=POLL_TIMEOUT + 10) as resp:
            result = json.loads(resp.read())
            if not result.get("ok"):
                log.error("Telegram API error: %s %s", method, result.get("description", ""))
            return result
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")[:200]
        log.error("Telegram API HTTP %d for %s: %s", e.code, method, body)
        raise
    except urllib.error.URLError as e:
        log.error("Telegram API network error for %s: %s", method, e.reason)
        raise


def send_message(chat_id, text: str) -> bool:
    """Send a text message to Telegram chat. Returns True if all chunks sent."""
    if not text:
        return True
    chat_id = str(chat_id)
    success = True
    # Telegram limit: 4096 chars
    for i in range(0, len(text), 4000):
        chunk = text[i:i + 4000]
        try:
            tg_api("sendMessage", {
                "chat_id": chat_id,
                "text": chunk,
                "parse_mode": "Markdown",
            })
        except Exception as md_err:
            log.warning("Markdown send failed, retrying plain: %s", md_err)
            # Retry without markdown if parsing fails
            try:
                tg_api("sendMessage", {
                    "chat_id": chat_id,
                    "text": chunk,
                })
            except Exception as e:
                log.error("Failed to send message chunk %d: %s", i // 4000, e)
                success = False
    return success


def handle_health(chat_id):
    """Return system health summary."""
    chat_id = str(chat_id)
    try:
        url = "http://localhost:8003/api/v1/health"
        req = urllib.request.Request(url, headers={"Origin": "http://localhost:3000"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read())
        lines = [f"*Vezir Health* — {d['status'].upper()}"]
        for k, v in d.get("components", {}).items():
            icon = "✅" if v["status"] == "ok" else "⚠️" if v["status"] == "degraded" else "❌"
            lines.append(f"{icon} {v['name']}: {v.get('detail', '')[:60]}")
        send_message(chat_id, "\n".join(lines))
    except Exception as e:
        send_message(chat_id, f"Health check failed: {e}")


def handle_status(chat_id):
    """Return running missions."""
    chat_id = str(chat_id)
    try:
        url = "http://localhost:8003/api/v1/missions"
        req = urllib.request.Request(url, headers={"Origin": "http://localhost:3000"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            d = json.loads(resp.read())
        missions = d.get("missions", [])
        active = [m for m in missions if m.get("state") in
                  ("running", "planning", "executing", "pending")]
        if not active:
            send_message(chat_id, "Aktif mission yok.")
            return
        lines = [f"*Aktif Missionlar* ({len(active)})"]
        for m in active[:5]:
            lines.append(f"• `{m['missionId'][:25]}` — {m['state']} — {m.get('goal', '')[:50]}")
        send_message(chat_id, "\n".join(lines))
    except Exception as e:
        send_message(chat_id, f"Status check failed: {e}")


def handle_agent_message(chat_id, text: str, mission_mode: bool = False):
    """Run oc-agent-runner and return result."""
    chat_id = str(chat_id)
    mode_label = "MISSION" if mission_mode else "AGENT"
    send_message(chat_id, f"⏳ {mode_label} calisiyor...")

    # Verify agent script exists
    if not os.path.isfile(AGENT_SCRIPT):
        log.error("Agent script not found: %s", AGENT_SCRIPT)
        send_message(chat_id, f"❌ Agent script bulunamadi: {AGENT_SCRIPT}")
        return

    cmd = [
        PYTHON_EXE, AGENT_SCRIPT,
        "--message", text,
        "--agent", "gpt-general",
        "--user-id", str(chat_id),
        "--session-id", f"tg-{int(time.time())}-{os.getpid()}",
        "--max-turns", "10",
    ]
    if mission_mode:
        cmd.append("--mission")

    def _run():
        try:
            log.info("Running %s: %s", mode_label, " ".join(cmd[:4]) + "...")
            r = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=AGENT_TIMEOUT,
                cwd=os.path.dirname(AGENT_SCRIPT),
                env={**os.environ, "PYTHONIOENCODING": "utf-8"},
            )
            if r.returncode != 0:
                log.warning("%s exited with code %d", mode_label, r.returncode)
                if r.stderr:
                    log.warning("%s stderr: %s", mode_label, r.stderr[:500])

            output = r.stdout.strip()
            if output:
                try:
                    result = json.loads(output)
                    if mission_mode:
                        status = result.get("status", "?")
                        mid = result.get("missionId", "")
                        summary = result.get("summary", "")
                        reply = f"*Mission {status}*\nID: `{mid}`"
                        if summary:
                            reply += f"\n\n{summary[:2000]}"
                    elif result.get("response"):
                        reply = result["response"][:3000]
                    else:
                        reply = output[:3000]
                except json.JSONDecodeError:
                    reply = output[:3000]
            else:
                stderr_info = r.stderr[:500] if r.stderr else "no output"
                reply = f"Agent cikti vermedi (exit={r.returncode}).\n{stderr_info}"
                log.error("Agent produced no output. exit=%d stderr=%s", r.returncode, stderr_info[:200])
            if not send_message(chat_id, reply):
                log.error("Prompt gonderilemedi — message delivery failed for chat %s", chat_id)
        except subprocess.TimeoutExpired:
            log.error("%s timeout after %ds", mode_label, AGENT_TIMEOUT)
            send_message(chat_id, f"⏰ {mode_label} {AGENT_TIMEOUT}s timeout.")
        except Exception as e:
            log.error("%s error: %s: %s", mode_label, type(e).__name__, e)
            send_message(chat_id, f"❌ Hata: {type(e).__name__}: {e}")

    # Run in thread to not block polling
    t = threading.Thread(target=_run, daemon=True, name=f"agent-{int(time.time())}")
    t.start()


def main():
    _resolve_token()
    if not BOT_TOKEN:
        log.error("Bot token bulunamadi! OC_TELEGRAM_BOT_TOKEN veya WSL .env gerekli.")
        sys.exit(1)

    # Verify bot
    me = tg_api("getMe")
    bot_name = me["result"]["username"]
    log.info("Bot basladi: @%s  chat=%s", bot_name, CHAT_ID)

    offset = None

    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "limit": 10}
            if offset:
                params["offset"] = offset

            updates = tg_api("getUpdates", params)

            for update in updates.get("result", []):
                offset = update["update_id"] + 1
                msg = update.get("message")
                if not msg:
                    continue

                chat_id = msg.get("chat", {}).get("id")
                text = (msg.get("text") or "").strip()
                username = msg.get("from", {}).get("username", "?")

                if not text or not chat_id:
                    continue

                # Security: only respond to configured chat
                if str(chat_id) != str(CHAT_ID):
                    log.warning("Unauthorized chat: %s from @%s", chat_id, username)
                    continue

                log.info("@%s: %s", username, text[:80])

                # Route commands
                if text.lower() in ("/health", "health", "/saglik"):
                    handle_health(chat_id)
                elif text.lower() in ("/status", "status", "/durum"):
                    handle_status(chat_id)
                elif text.lower().startswith("/mission "):
                    handle_agent_message(chat_id, text[9:].strip(), mission_mode=True)
                elif text.lower() in ("/help", "help", "/yardim"):
                    send_message(chat_id,
                        "*Vezir Telegram Bot*\n\n"
                        "Komutlar:\n"
                        "• `/health` — Sistem sagligi\n"
                        "• `/status` — Aktif missionlar\n"
                        "• `/mission <goal>` — Multi-agent mission baslat\n"
                        "• Normal mesaj — Tek turlu agent\n"
                        "• `/help` — Bu mesaj")
                else:
                    handle_agent_message(chat_id, text, mission_mode=False)

        except urllib.error.URLError as e:
            log.warning("Network error: %s — retrying in 5s", e)
            time.sleep(5)
        except KeyboardInterrupt:
            log.info("Bot durduruluyor...")
            break
        except Exception as e:
            log.error("Polling error: %s", e)
            time.sleep(3)


if __name__ == "__main__":
    main()
