"""Quality tests — Task 14.23.

Health endpoint contract test, Telegram bot unit tests,
WMCP tool inventory verification.
"""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestHealthContract(unittest.TestCase):
    """Health endpoint returns expected component structure."""

    def setUp(self):
        import asyncio

        from httpx import ASGITransport, AsyncClient

        from api.server import app
        self.loop = asyncio.new_event_loop()
        self.client = self.loop.run_until_complete(
            AsyncClient(
                transport=ASGITransport(app=app),
                base_url="http://testserver"
            ).__aenter__()
        )

    def tearDown(self):
        self.loop.run_until_complete(self.client.__aexit__(None, None, None))
        self.loop.close()

    def _get(self, path):
        return self.loop.run_until_complete(self.client.get(path))

    def test_health_returns_200(self):
        r = self._get("/api/v1/health")
        self.assertEqual(r.status_code, 200)

    def test_health_has_status(self):
        data = self._get("/api/v1/health").json()
        self.assertIn("status", data)
        self.assertIn(data["status"], ("ok", "degraded", "error"))

    def test_health_has_components(self):
        data = self._get("/api/v1/health").json()
        self.assertIn("components", data)
        self.assertIsInstance(data["components"], dict)

    def test_health_api_component_present(self):
        data = self._get("/api/v1/health").json()
        self.assertIn("api", data["components"])
        self.assertEqual(data["components"]["api"]["status"], "ok")

    def test_health_has_meta(self):
        data = self._get("/api/v1/health").json()
        self.assertIn("meta", data)
        self.assertIn("generatedAt", data["meta"])


class TestTelegramBotModule(unittest.TestCase):
    """Telegram bot module imports and has expected structure."""

    def test_module_imports(self):
        import telegram_bot
        self.assertTrue(hasattr(telegram_bot, "CHAT_ID"))
        self.assertTrue(hasattr(telegram_bot, "handle_health"))
        self.assertTrue(hasattr(telegram_bot, "handle_status"))
        self.assertTrue(hasattr(telegram_bot, "handle_agent_message"))

    def test_handlers_callable(self):
        """Command handlers exist and are callable."""
        import telegram_bot
        self.assertTrue(callable(telegram_bot.handle_health))
        self.assertTrue(callable(telegram_bot.handle_status))
        self.assertTrue(callable(telegram_bot.handle_agent_message))

    def test_chat_id_is_string(self):
        import telegram_bot
        self.assertIsInstance(telegram_bot.CHAT_ID, str)
        self.assertTrue(len(telegram_bot.CHAT_ID) > 0)


class TestWMCPToolInventory(unittest.TestCase):
    """WMCP tool catalog has expected tool count and structure."""

    def test_tool_catalog_loads(self):
        from services.tool_catalog import get_tools_for_openai
        tools = get_tools_for_openai()
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 0)

    def test_tools_have_function_schema(self):
        from services.tool_catalog import get_tools_for_openai
        tools = get_tools_for_openai()
        for t in tools:
            self.assertIn("function", t)
            self.assertIn("name", t["function"])
            self.assertIn("description", t["function"])

    def test_tool_count_at_least_18(self):
        """Advance plan claims 18 WMCP tools."""
        from services.tool_catalog import get_tools_for_openai
        tools = get_tools_for_openai()
        self.assertGreaterEqual(len(tools), 18,
                                f"Expected ≥18 tools, got {len(tools)}")

    def test_known_tools_present(self):
        """Critical tools must be in catalog."""
        from services.tool_catalog import get_tools_for_openai
        tool_names = {t["function"]["name"] for t in get_tools_for_openai()}
        expected = {"read_file", "list_directory", "get_system_info",
                    "get_system_health"}
        missing = expected - tool_names
        self.assertEqual(missing, set(),
                         f"Missing critical tools: {missing}")
