"""Tests for AzureHealthCheck + retirement guard (D-148)."""
import datetime
from unittest.mock import MagicMock, patch

from providers.azure_health import AzureHealthCheck, AzureHealthStatus

# --- Fixtures ---

MOCK_ENDPOINT = "https://test.openai.azure.com"
MOCK_DEPLOYMENT = "test-deploy"
MOCK_KEY = "test-key"


def make_checker(**overrides):
    defaults = {
        "endpoint": MOCK_ENDPOINT,
        "deployment": MOCK_DEPLOYMENT,
        "api_key": MOCK_KEY,
    }
    defaults.update(overrides)
    return AzureHealthCheck(**defaults)


# --- Retirement guard tests ---


class TestRetirementGuard:
    def test_no_retirement_date(self):
        hc = make_checker()
        result = hc._check_retirement()
        assert result is None

    def test_past_retirement(self):
        hc = make_checker(retirement_date="2020-01-01")
        result = hc._check_retirement()
        assert result is not None
        assert result.status == "retired"
        assert not result.healthy
        assert result.retirement_days < 0

    def test_near_retirement_30_days(self):
        near = (datetime.datetime.now() + datetime.timedelta(days=20)).strftime("%Y-%m-%d")
        hc = make_checker(retirement_date=near)
        result = hc._check_retirement()
        assert result is not None
        assert result.status == "degraded"
        assert result.healthy
        assert 0 < result.retirement_days <= 30

    def test_far_future_retirement(self):
        hc = make_checker(retirement_date="2099-12-31")
        result = hc._check_retirement()
        assert result is None  # No warning needed

    def test_invalid_retirement_date(self):
        hc = make_checker(retirement_date="invalid-date")
        result = hc._check_retirement()
        assert result is None


# --- Health check tests ---


class TestHealthCheck:
    @patch("providers.azure_health.requests.post")
    def test_healthy_endpoint(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "completed"}
        mock_post.return_value = mock_resp

        hc = make_checker()
        result = hc.check()
        assert result.healthy
        assert result.status == "ok"
        assert result.latency_ms is not None
        assert result.deployment == MOCK_DEPLOYMENT

    @patch("providers.azure_health.requests.post")
    def test_401_auth_failure(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_post.return_value = mock_resp

        hc = make_checker()
        result = hc.check()
        assert not result.healthy
        assert result.status == "unhealthy"
        assert "401" in result.detail

    @patch("providers.azure_health.requests.post")
    def test_404_deployment_missing(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_post.return_value = mock_resp

        hc = make_checker()
        result = hc.check()
        assert not result.healthy
        assert "not found" in result.detail

    @patch("providers.azure_health.requests.post")
    def test_429_rate_limited(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 429
        mock_post.return_value = mock_resp

        hc = make_checker()
        result = hc.check()
        assert result.healthy  # Still healthy, just degraded
        assert result.status == "degraded"

    @patch("providers.azure_health.requests.post")
    def test_500_server_error(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_resp.text = "Internal Server Error"
        mock_post.return_value = mock_resp

        hc = make_checker()
        result = hc.check()
        assert not result.healthy
        assert result.status == "unhealthy"

    @patch("providers.azure_health.requests.post")
    def test_timeout(self, mock_post):
        import requests as req
        mock_post.side_effect = req.Timeout()

        hc = make_checker()
        result = hc.check()
        assert not result.healthy
        assert result.status == "unreachable"

    @patch("providers.azure_health.requests.post")
    def test_connection_error(self, mock_post):
        import requests as req
        mock_post.side_effect = req.ConnectionError()

        hc = make_checker()
        result = hc.check()
        assert not result.healthy
        assert result.status == "unreachable"

    def test_missing_config(self):
        hc = AzureHealthCheck(endpoint="", deployment="test", api_key="")
        result = hc.check()
        assert not result.healthy
        assert "Missing" in result.detail


# --- Retirement + health combined ---


class TestRetirementWithHealth:
    def test_retired_skips_probe(self):
        """Past retirement → immediately unhealthy without network call."""
        hc = make_checker(retirement_date="2020-01-01")
        result = hc.check()
        assert not result.healthy
        assert result.status == "retired"
        # No network call was made (no mock needed)

    @patch("providers.azure_health.requests.post")
    def test_near_retirement_with_healthy_endpoint(self, mock_post):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.json.return_value = {"status": "completed"}
        mock_post.return_value = mock_resp

        near = (datetime.datetime.now() + datetime.timedelta(days=10)).strftime("%Y-%m-%d")
        hc = make_checker(retirement_date=near)
        result = hc.check()
        assert result.status == "degraded"  # Healthy but near retirement
        assert result.retirement_days is not None
        assert result.retirement_days <= 30


# --- AzureHealthStatus dataclass tests ---


class TestAzureHealthStatus:
    def test_basic_fields(self):
        status = AzureHealthStatus(
            healthy=True,
            status="ok",
            detail="all good",
            deployment="test",
        )
        assert status.healthy
        assert status.latency_ms is None
        assert status.retirement_days is None

    def test_full_fields(self):
        status = AzureHealthStatus(
            healthy=False,
            status="retired",
            detail="retired",
            deployment="old-deploy",
            latency_ms=150.5,
            retirement_days=-30,
        )
        assert not status.healthy
        assert status.latency_ms == 150.5
        assert status.retirement_days == -30
