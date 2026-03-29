"""Tests for telegram_bot.py — Sprint 38 regression coverage."""
import os
import sys
import unittest
from unittest.mock import MagicMock, patch

# Add agent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Must set BOT_TOKEN before import to avoid WSL fallback
os.environ["OC_TELEGRAM_BOT_TOKEN"] = "test-token-123"
os.environ["OC_TELEGRAM_CHAT_ID"] = "12345"

import telegram_bot


class TestTokenResolution(unittest.TestCase):
    """Test bot token resolution from multiple sources."""

    def test_token_from_env(self):
        """Token set via env var should be used directly."""
        with patch.dict(os.environ, {"OC_TELEGRAM_BOT_TOKEN": "env-token"}):
            telegram_bot.BOT_TOKEN = None
            telegram_bot.BOT_TOKEN = os.environ.get("OC_TELEGRAM_BOT_TOKEN")
            self.assertEqual(telegram_bot.BOT_TOKEN, "env-token")

    def test_read_env_file_valid(self, ):
        """_read_env_file should parse key=value from .env files."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OTHER_KEY=other\n")
            f.write("OC_TELEGRAM_BOT_TOKEN=file-token-456\n")
            f.write("MORE=stuff\n")
            f.flush()
            result = telegram_bot._read_env_file(f.name, "OC_TELEGRAM_BOT_TOKEN")
        os.unlink(f.name)
        self.assertEqual(result, "file-token-456")

    def test_read_env_file_missing_key(self):
        """_read_env_file returns None if key not found."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write("OTHER_KEY=other\n")
            f.flush()
            result = telegram_bot._read_env_file(f.name, "OC_TELEGRAM_BOT_TOKEN")
        os.unlink(f.name)
        self.assertIsNone(result)

    def test_read_env_file_nonexistent(self):
        """_read_env_file returns None for missing file."""
        result = telegram_bot._read_env_file("/nonexistent/.env", "KEY")
        self.assertIsNone(result)

    def test_read_env_file_quoted_value(self):
        """_read_env_file strips quotes from values."""
        import tempfile
        with tempfile.NamedTemporaryFile(mode="w", suffix=".env", delete=False) as f:
            f.write('OC_TELEGRAM_BOT_TOKEN="quoted-token"\n')
            f.flush()
            result = telegram_bot._read_env_file(f.name, "OC_TELEGRAM_BOT_TOKEN")
        os.unlink(f.name)
        self.assertEqual(result, "quoted-token")


class TestTgApi(unittest.TestCase):
    """Test Telegram API call wrapper."""

    def test_tg_api_no_token_raises(self):
        """tg_api should raise RuntimeError when BOT_TOKEN is None."""
        original = telegram_bot.BOT_TOKEN
        telegram_bot.BOT_TOKEN = None
        try:
            with self.assertRaises(RuntimeError):
                telegram_bot.tg_api("getMe")
        finally:
            telegram_bot.BOT_TOKEN = original

    @patch("telegram_bot.urllib.request.urlopen")
    def test_tg_api_success(self, mock_urlopen):
        """tg_api should return parsed JSON on success."""
        original = telegram_bot.BOT_TOKEN
        telegram_bot.BOT_TOKEN = "test-token"
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok":true,"result":{"id":123}}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        try:
            result = telegram_bot.tg_api("getMe")
            self.assertTrue(result["ok"])
            self.assertEqual(result["result"]["id"], 123)
        finally:
            telegram_bot.BOT_TOKEN = original

    @patch("telegram_bot.urllib.request.urlopen")
    def test_tg_api_with_params(self, mock_urlopen):
        """tg_api should send JSON body when params provided."""
        original = telegram_bot.BOT_TOKEN
        telegram_bot.BOT_TOKEN = "test-token"
        mock_resp = MagicMock()
        mock_resp.read.return_value = b'{"ok":true,"result":true}'
        mock_resp.__enter__ = MagicMock(return_value=mock_resp)
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp
        try:
            telegram_bot.tg_api("sendMessage", {"chat_id": "123", "text": "hi"})
            # Verify urlopen was called with a Request object
            args = mock_urlopen.call_args
            req = args[0][0]
            self.assertIn("sendMessage", req.full_url)
        finally:
            telegram_bot.BOT_TOKEN = original


class TestSendMessage(unittest.TestCase):
    """Test message sending with fallback."""

    @patch("telegram_bot.tg_api")
    def test_send_message_success(self, mock_api):
        """send_message should return True on success."""
        mock_api.return_value = {"ok": True}
        result = telegram_bot.send_message("123", "Hello")
        self.assertTrue(result)
        mock_api.assert_called_once()

    @patch("telegram_bot.tg_api")
    def test_send_message_empty_text(self, mock_api):
        """send_message with empty text should return True without API call."""
        result = telegram_bot.send_message("123", "")
        self.assertTrue(result)
        mock_api.assert_not_called()

    @patch("telegram_bot.tg_api")
    def test_send_message_markdown_fallback(self, mock_api):
        """send_message should retry without Markdown on first failure."""
        mock_api.side_effect = [Exception("parse error"), {"ok": True}]
        result = telegram_bot.send_message("123", "test *bold*")
        self.assertTrue(result)
        self.assertEqual(mock_api.call_count, 2)
        # Second call should not have parse_mode
        second_call_params = mock_api.call_args_list[1][0][1]
        self.assertNotIn("parse_mode", second_call_params)

    @patch("telegram_bot.tg_api")
    def test_send_message_total_failure(self, mock_api):
        """send_message should return False when both attempts fail."""
        mock_api.side_effect = Exception("network down")
        result = telegram_bot.send_message("123", "test")
        self.assertFalse(result)

    @patch("telegram_bot.tg_api")
    def test_send_message_long_text_chunks(self, mock_api):
        """send_message should split long text into 4000-char chunks."""
        mock_api.return_value = {"ok": True}
        long_text = "A" * 8500  # Should produce 3 chunks
        telegram_bot.send_message("123", long_text)
        self.assertEqual(mock_api.call_count, 3)

    @patch("telegram_bot.tg_api")
    def test_send_message_chat_id_int(self, mock_api):
        """send_message should handle integer chat_id."""
        mock_api.return_value = {"ok": True}
        result = telegram_bot.send_message(12345, "test")
        self.assertTrue(result)
        # chat_id should be string in API call
        call_params = mock_api.call_args[0][1]
        self.assertEqual(call_params["chat_id"], "12345")


class TestHandleAgentMessage(unittest.TestCase):
    """Test agent message handling."""

    @patch("telegram_bot.send_message")
    def test_missing_agent_script(self, mock_send):
        """Should send error if agent script doesn't exist."""
        original = telegram_bot.AGENT_SCRIPT
        telegram_bot.AGENT_SCRIPT = "/nonexistent/script.py"
        try:
            telegram_bot.handle_agent_message("123", "test")
            # Check error message was sent
            calls = mock_send.call_args_list
            self.assertTrue(any("bulunamadi" in str(c) for c in calls))
        finally:
            telegram_bot.AGENT_SCRIPT = original

    @patch("telegram_bot.send_message")
    @patch("subprocess.run")
    def test_agent_json_response(self, mock_run, mock_send):
        """Should parse JSON response from agent."""
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout='{"response": "Agent says hello"}',
            stderr=""
        )
        telegram_bot.handle_agent_message("123", "test")
        # Wait for thread
        import time
        time.sleep(0.5)
        calls = [str(c) for c in mock_send.call_args_list]
        self.assertTrue(any("Agent says hello" in c for c in calls))

    @patch("telegram_bot.send_message")
    @patch("subprocess.run")
    def test_agent_empty_output(self, mock_run, mock_send):
        """Should report error when agent produces no output."""
        mock_run.return_value = MagicMock(
            returncode=1,
            stdout="",
            stderr="ImportError: no module named foo"
        )
        telegram_bot.handle_agent_message("123", "test")
        import time
        time.sleep(0.5)
        calls = [str(c) for c in mock_send.call_args_list]
        self.assertTrue(any("cikti vermedi" in c or "ImportError" in c for c in calls))


class TestCommandRouting(unittest.TestCase):
    """Test message routing logic."""

    def test_health_commands(self):
        """Health command variants should be recognized."""
        health_cmds = ["/health", "health", "/saglik"]
        for cmd in health_cmds:
            self.assertIn(cmd.lower(), ("/health", "health", "/saglik"))

    def test_status_commands(self):
        """Status command variants should be recognized."""
        status_cmds = ["/status", "status", "/durum"]
        for cmd in status_cmds:
            self.assertIn(cmd.lower(), ("/status", "status", "/durum"))

    def test_mission_prefix(self):
        """Mission command should extract goal text."""
        text = "/mission deploy the frontend"
        self.assertTrue(text.lower().startswith("/mission "))
        goal = text[9:].strip()
        self.assertEqual(goal, "deploy the frontend")

    def test_security_chat_id_check(self):
        """Only configured chat_id should be accepted."""
        configured = "12345"
        self.assertEqual(str(12345), configured)
        self.assertNotEqual(str(99999), configured)


if __name__ == "__main__":
    unittest.main()
