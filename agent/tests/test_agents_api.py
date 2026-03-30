"""B-108 Agent Health API tests — Sprint 46."""
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestProviderLiveness(unittest.TestCase):
    """Unit tests for provider liveness checks."""

    def test_check_openai_with_key(self):
        from api.agents_api import _check_provider_liveness
        with unittest.mock.patch.dict(os.environ, {"OPENAI_API_KEY": "sk-test"}):
            result = _check_provider_liveness("openai")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["provider"], "openai")

    def test_check_openai_without_key(self):
        from api.agents_api import _check_provider_liveness
        env = os.environ.copy()
        env.pop("OPENAI_API_KEY", None)
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            result = _check_provider_liveness("openai")
            self.assertEqual(result["status"], "unavailable")

    def test_check_anthropic_with_key(self):
        from api.agents_api import _check_provider_liveness
        with unittest.mock.patch.dict(os.environ, {"ANTHROPIC_API_KEY": "sk-ant-test"}):
            result = _check_provider_liveness("anthropic")
            self.assertEqual(result["status"], "ok")
            self.assertEqual(result["model"], "claude-sonnet")

    def test_check_ollama_without_url(self):
        from api.agents_api import _check_provider_liveness
        env = os.environ.copy()
        env.pop("OLLAMA_URL", None)
        env.pop("OLLAMA_HOST", None)
        with unittest.mock.patch.dict(os.environ, env, clear=True):
            result = _check_provider_liveness("ollama")
            self.assertEqual(result["status"], "unavailable")

    def test_check_unknown_provider(self):
        from api.agents_api import _check_provider_liveness
        result = _check_provider_liveness("something")
        self.assertEqual(result["status"], "unknown")


class TestAgentsAPIEndpoints(unittest.TestCase):
    """Integration tests for agent health API endpoints."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("VEZIR_DEV", "1")
        from fastapi.testclient import TestClient
        from api.server import app
        cls.client = TestClient(app)

    def test_providers_endpoint(self):
        resp = self.client.get("/api/v1/agents/providers")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("meta", data)
        self.assertIn("providers", data)
        self.assertIn("available_count", data)
        self.assertIn("total_count", data)
        self.assertEqual(data["total_count"], 3)
        for p in data["providers"]:
            self.assertIn("name", p)
            self.assertIn("status", p)
            self.assertIn("provider", p)

    def test_roles_endpoint(self):
        resp = self.client.get("/api/v1/agents/roles")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("roles", data)
        self.assertIn("total", data)
        self.assertEqual(data["total"], 9)
        for role in data["roles"]:
            self.assertIn("id", role)
            self.assertIn("displayName", role)
            self.assertIn("toolPolicy", role)
            self.assertIn("toolCount", role)
            self.assertIn("preferredModel", role)

    def test_capability_matrix_endpoint(self):
        resp = self.client.get("/api/v1/agents/capability-matrix")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("matrix", data)
        self.assertEqual(len(data["matrix"]), 9)
        for entry in data["matrix"]:
            self.assertIn("role", entry)
            self.assertIn("preferredModel", entry)
            self.assertIn("modelTier", entry)
            self.assertIn("toolPolicy", entry)
            self.assertIn("canExpand", entry)

    def test_performance_endpoint(self):
        resp = self.client.get("/api/v1/agents/performance")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("performance", data)
        self.assertIsInstance(data["performance"], list)

    def test_roles_contain_all_canonical(self):
        resp = self.client.get("/api/v1/agents/roles")
        data = resp.json()
        role_ids = {r["id"] for r in data["roles"]}
        expected = {"product-owner", "analyst", "architect", "project-manager",
                    "developer", "tester", "reviewer", "manager", "remote-operator"}
        self.assertEqual(role_ids, expected)


import unittest.mock


if __name__ == "__main__":
    unittest.main()
