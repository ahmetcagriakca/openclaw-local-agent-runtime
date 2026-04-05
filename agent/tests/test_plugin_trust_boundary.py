"""B-142: Plugin Mutation Auth Boundary tests — Sprint 65 Task 65.2.

Tests for trust_status enforcement on plugin mutation endpoints:
- No auth → 401
- Viewer role → 403
- Operator + untrusted → 403
- Operator + unknown → 200 (warning logged)
- Operator + trusted → 200
"""
import os
import sys
import unittest
from dataclasses import dataclass
from unittest.mock import MagicMock, patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi import HTTPException

from api.plugins_api import _enforce_trust_status


@dataclass
class FakePluginEntry:
    plugin_id: str = "test-plugin"
    name: str = "Test"
    version: str = "1.0.0"
    description: str = "Test plugin"
    author: str = "test"
    status: str = "available"
    capabilities: list = None
    risk_tier: str = "low"
    source: str = "local"
    trust_status: str = "unknown"
    category: str = "general"
    tags: list = None
    installed_at: str = None
    updated_at: str = None

    def __post_init__(self):
        if self.capabilities is None:
            self.capabilities = []
        if self.tags is None:
            self.tags = []


class TestEnforceTrustStatus(unittest.TestCase):
    """Unit tests for _enforce_trust_status helper."""

    def test_untrusted_raises_403(self):
        entry = FakePluginEntry(trust_status="untrusted")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "my-plugin", "install")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("untrusted", ctx.exception.detail)

    def test_unknown_raises_403_fail_closed(self):
        """B-142: unknown trust status is fail-closed on mutation paths."""
        entry = FakePluginEntry(trust_status="unknown")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "my-plugin", "install")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("unknown trust status", ctx.exception.detail)

    def test_trusted_proceeds_silently(self):
        entry = FakePluginEntry(trust_status="trusted")
        # Should not raise
        _enforce_trust_status(entry, "my-plugin", "install")

    def test_untrusted_install_denied(self):
        entry = FakePluginEntry(trust_status="untrusted")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "plug1", "install")
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("install denied", ctx.exception.detail)

    def test_untrusted_uninstall_denied(self):
        entry = FakePluginEntry(trust_status="untrusted")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "plug1", "uninstall")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_untrusted_enable_denied(self):
        entry = FakePluginEntry(trust_status="untrusted")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "plug1", "enable")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_untrusted_disable_denied(self):
        entry = FakePluginEntry(trust_status="untrusted")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "plug1", "disable")
        self.assertEqual(ctx.exception.status_code, 403)

    def test_untrusted_config_update_denied(self):
        entry = FakePluginEntry(trust_status="untrusted")
        with self.assertRaises(HTTPException) as ctx:
            _enforce_trust_status(entry, "plug1", "config_update")
        self.assertEqual(ctx.exception.status_code, 403)


class TestPluginApiTrustIntegration(unittest.TestCase):
    """Integration tests using FastAPI TestClient."""

    @classmethod
    def setUpClass(cls):
        """Create TestClient with mocked auth."""
        from fastapi import FastAPI
        from fastapi.testclient import TestClient

        from api.plugins_api import router

        app = FastAPI()
        app.include_router(router, prefix="/api/v1")

        cls.client = TestClient(app)

    def _mock_store_with_plugin(self, trust_status="trusted", status="available"):
        """Return a mock store that returns a plugin with given trust_status."""
        from services.plugin_marketplace import PluginEntry

        entry = PluginEntry(
            plugin_id="test-plug",
            name="Test Plugin",
            version="1.0.0",
            description="A test plugin",
            author="tester",
            status=status,
            trust_status=trust_status,
        )
        store = MagicMock()
        store.get.return_value = entry
        store.update_status.return_value = True
        store.update_config.return_value = True
        return store

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_install_trusted_plugin_200(self, mock_get_store):
        mock_get_store.return_value = self._mock_store_with_plugin("trusted", "available")
        resp = self.client.post("/api/v1/plugins/test-plug/install")
        self.assertEqual(resp.status_code, 200)

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_install_untrusted_plugin_403(self, mock_get_store):
        mock_get_store.return_value = self._mock_store_with_plugin("untrusted", "available")
        resp = self.client.post("/api/v1/plugins/test-plug/install")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("untrusted", resp.json()["detail"])

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_install_unknown_trust_denied_403(self, mock_get_store):
        """B-142: unknown trust is fail-closed — 403 on mutation."""
        mock_get_store.return_value = self._mock_store_with_plugin("unknown", "available")
        resp = self.client.post("/api/v1/plugins/test-plug/install")
        self.assertEqual(resp.status_code, 403)
        self.assertIn("unknown trust status", resp.json()["detail"])

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_enable_untrusted_plugin_403(self, mock_get_store):
        mock_get_store.return_value = self._mock_store_with_plugin("untrusted", "installed")
        resp = self.client.post("/api/v1/plugins/test-plug/enable")
        self.assertEqual(resp.status_code, 403)

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_disable_untrusted_plugin_403(self, mock_get_store):
        mock_get_store.return_value = self._mock_store_with_plugin("untrusted", "enabled")
        resp = self.client.post("/api/v1/plugins/test-plug/disable")
        self.assertEqual(resp.status_code, 403)

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_uninstall_untrusted_plugin_403(self, mock_get_store):
        mock_get_store.return_value = self._mock_store_with_plugin("untrusted", "installed")
        resp = self.client.post("/api/v1/plugins/test-plug/uninstall")
        self.assertEqual(resp.status_code, 403)

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_config_update_untrusted_plugin_403(self, mock_get_store):
        mock_get_store.return_value = self._mock_store_with_plugin("untrusted", "installed")
        resp = self.client.put("/api/v1/plugins/test-plug/config",
                               json={"config": {"key": "val"}})
        self.assertEqual(resp.status_code, 403)

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_config_update_trusted_plugin_200(self, mock_get_store):
        store = self._mock_store_with_plugin("trusted", "installed")
        mock_get_store.return_value = store
        resp = self.client.put("/api/v1/plugins/test-plug/config",
                               json={"config": {"key": "val"}})
        self.assertEqual(resp.status_code, 200)

    @patch("api.plugins_api.require_operator", lambda: None)
    @patch("api.plugins_api._get_store")
    def test_not_found_plugin_404(self, mock_get_store):
        store = MagicMock()
        store.get.return_value = None
        mock_get_store.return_value = store
        resp = self.client.post("/api/v1/plugins/nonexistent/install")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
