# conftest.py - pytest configuration
# Disable pytest-anyio plugin to prevent event loop conflicts
# with asyncio.run() used in SSE tests and TestClient.

def pytest_configure(config):
    """Unregister anyio plugin if present - prevents event loop conflicts."""
    try:
        plugin = config.pluginmanager.get_plugin("anyio")
        if plugin:
            config.pluginmanager.unregister(plugin)
    except Exception:
        pass
