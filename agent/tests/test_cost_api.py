"""B-105 Cost API tests — Sprint 46."""
import os
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestCostEstimation(unittest.TestCase):
    """Unit tests for cost estimation logic."""

    def test_estimate_cost_gpt4o(self):
        from api.cost_api import _estimate_cost
        cost = _estimate_cost(10000, "gpt-4o")
        # 6000 input * 0.0025/1K + 4000 output * 0.01/1K = 15 + 40 = 0.055
        self.assertAlmostEqual(cost, 0.055, places=3)

    def test_estimate_cost_claude(self):
        from api.cost_api import _estimate_cost
        cost = _estimate_cost(10000, "claude-sonnet")
        # 6000 * 0.003/1K + 4000 * 0.015/1K = 18 + 60 = 0.078
        self.assertAlmostEqual(cost, 0.078, places=3)

    def test_estimate_cost_ollama_free(self):
        from api.cost_api import _estimate_cost
        cost = _estimate_cost(10000, "ollama")
        self.assertEqual(cost, 0.0)

    def test_estimate_cost_unknown_provider(self):
        from api.cost_api import _estimate_cost
        cost = _estimate_cost(10000, "unknown-provider")
        self.assertGreater(cost, 0)

    def test_estimate_cost_zero_tokens(self):
        from api.cost_api import _estimate_cost
        cost = _estimate_cost(0, "gpt-4o")
        self.assertEqual(cost, 0.0)


class TestCostAPIEndpoints(unittest.TestCase):
    """Integration tests for cost API endpoints via TestClient."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("VEZIR_DEV", "1")
        from fastapi.testclient import TestClient
        from api.server import app
        cls.client = TestClient(app)

    def test_cost_summary_endpoint(self):
        resp = self.client.get("/api/v1/cost/summary")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("meta", data)
        self.assertIn("total_missions", data)
        self.assertIn("total_estimated_cost", data)
        self.assertIn("provider_breakdown", data)
        self.assertIn("success_rate", data)
        self.assertIn("pricing_model", data)

    def test_cost_missions_endpoint(self):
        resp = self.client.get("/api/v1/cost/missions")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("meta", data)
        self.assertIn("total", data)
        self.assertIn("missions", data)
        self.assertIsInstance(data["missions"], list)

    def test_cost_missions_sort_param(self):
        resp = self.client.get("/api/v1/cost/missions?sort=tokens_desc")
        self.assertEqual(resp.status_code, 200)

    def test_cost_trends_daily(self):
        resp = self.client.get("/api/v1/cost/trends?bucket=daily")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertIn("bucket", data)
        self.assertEqual(data["bucket"], "daily")
        self.assertIn("trends", data)
        self.assertIsInstance(data["trends"], list)

    def test_cost_trends_weekly(self):
        resp = self.client.get("/api/v1/cost/trends?bucket=weekly")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["bucket"], "weekly")

    def test_cost_trends_monthly(self):
        resp = self.client.get("/api/v1/cost/trends?bucket=monthly")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["bucket"], "monthly")

    def test_cost_trends_invalid_bucket(self):
        resp = self.client.get("/api/v1/cost/trends?bucket=invalid")
        self.assertEqual(resp.status_code, 422)

    def test_cost_summary_has_provider_pricing(self):
        resp = self.client.get("/api/v1/cost/summary")
        data = resp.json()
        pricing = data["pricing_model"]
        self.assertIn("gpt-4o", pricing)
        self.assertIn("input", pricing["gpt-4o"])
        self.assertIn("output", pricing["gpt-4o"])


if __name__ == "__main__":
    unittest.main()
