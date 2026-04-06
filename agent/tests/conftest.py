# conftest.py - pytest configuration
# Disable pytest-anyio plugin to prevent event loop conflicts
# with asyncio.run() used in SSE tests and TestClient.
import os

# Ensure throttle middleware is disabled during tests (B-005)
os.environ["TESTING"] = "1"

# Auth bypass for tests — no auth.json in test environment (S76 P1.4)
os.environ["VEZIR_AUTH_BYPASS"] = "1"

# Auth test headers (D-117) — use test operator key for mutation tests
AUTH_HEADERS = {"Authorization": "Bearer vz_test_operator_key_001"}
VIEWER_HEADERS = {"Authorization": "Bearer vz_test_viewer_key_001"}

def pytest_configure(config):
    """Unregister anyio plugin if present - prevents event loop conflicts."""
    try:
        plugin = config.pluginmanager.get_plugin("anyio")
        if plugin:
            config.pluginmanager.unregister(plugin)
    except Exception:
        pass
