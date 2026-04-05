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


class TestToolGovernanceManifest(unittest.TestCase):
    """B-144 S66: All 24 tools must carry complete governance metadata."""

    REQUIRED_GOVERNANCE_FIELDS = [
        "filesystemTouching", "mutationSurface",
        "workingSetScopeRequired", "requiresPathResolution",
        "reversibility", "idempotent", "side_effect_scope",
    ]
    VALID_REVERSIBILITY = {"none", "compensating", "full"}
    VALID_SIDE_EFFECT_SCOPE = {"local", "external", "irreversible"}

    def test_all_24_tools_have_governance(self):
        """Every tool in catalog must have a governance block."""
        from services.tool_catalog import TOOL_CATALOG
        self.assertEqual(len(TOOL_CATALOG), 24, f"Expected 24 tools, got {len(TOOL_CATALOG)}")
        for tool in TOOL_CATALOG:
            self.assertIn("governance", tool, f"{tool['name']}: missing governance block")

    def test_all_tools_have_7_required_fields(self):
        """Every tool governance block must have all 7 required fields."""
        from services.tool_catalog import TOOL_CATALOG
        for tool in TOOL_CATALOG:
            gov = tool.get("governance", {})
            for field in self.REQUIRED_GOVERNANCE_FIELDS:
                self.assertIn(field, gov, f"{tool['name']}: missing governance.{field}")

    def test_reversibility_values_valid(self):
        """reversibility must be none/compensating/full."""
        from services.tool_catalog import TOOL_CATALOG
        for tool in TOOL_CATALOG:
            val = tool["governance"]["reversibility"]
            self.assertIn(val, self.VALID_REVERSIBILITY,
                          f"{tool['name']}: invalid reversibility '{val}'")

    def test_idempotent_is_bool(self):
        """idempotent must be a boolean."""
        from services.tool_catalog import TOOL_CATALOG
        for tool in TOOL_CATALOG:
            val = tool["governance"]["idempotent"]
            self.assertIsInstance(val, bool, f"{tool['name']}: idempotent must be bool, got {type(val)}")

    def test_side_effect_scope_values_valid(self):
        """side_effect_scope must be local/external/irreversible."""
        from services.tool_catalog import TOOL_CATALOG
        for tool in TOOL_CATALOG:
            val = tool["governance"]["side_effect_scope"]
            self.assertIn(val, self.VALID_SIDE_EFFECT_SCOPE,
                          f"{tool['name']}: invalid side_effect_scope '{val}'")

    def test_validate_catalog_governance_zero_errors(self):
        """D-057 startup gate: validate_catalog_governance must return 0 errors."""
        from services.tool_catalog import validate_catalog_governance
        errors = validate_catalog_governance()
        self.assertEqual(len(errors), 0, f"Governance errors: {errors}")

    def test_irreversible_tools_have_none_reversibility(self):
        """Tools with side_effect_scope=irreversible must have reversibility=none."""
        from services.tool_catalog import TOOL_CATALOG
        for tool in TOOL_CATALOG:
            gov = tool["governance"]
            if gov["side_effect_scope"] == "irreversible":
                self.assertEqual(gov["reversibility"], "none",
                                 f"{tool['name']}: irreversible scope but reversibility={gov['reversibility']}")
