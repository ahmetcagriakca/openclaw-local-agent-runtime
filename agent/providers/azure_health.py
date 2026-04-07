"""Azure OpenAI health check + retirement guard (D-148)."""
import logging
import os
from dataclasses import dataclass
from datetime import datetime

import requests

logger = logging.getLogger(__name__)


@dataclass
class AzureHealthStatus:
    """Health check result for Azure OpenAI deployment."""

    healthy: bool
    status: str  # ok / degraded / unhealthy / retired / unreachable
    detail: str
    deployment: str
    latency_ms: float | None = None
    retirement_days: int | None = None


class AzureHealthCheck:
    """Health check for Azure OpenAI deployment.

    Checks:
    1. Endpoint reachability (lightweight probe)
    2. Retirement guard (30-day warning, past date = unhealthy)
    """

    def __init__(
        self,
        endpoint: str | None = None,
        deployment: str | None = None,
        api_key: str | None = None,
        api_version: str | None = None,
        retirement_date: str | None = None,
        timeout: int = 10,
    ):
        self.endpoint = (
            endpoint
            or os.environ.get("AZURE_OPENAI_ENDPOINT")
            or os.environ.get("APIM_ENDPOINT", "").split("/openai/")[0]
        )
        self.deployment = (
            deployment
            or os.environ.get("AZURE_OPENAI_DEPLOYMENT")
            or os.environ.get("APIM_MODEL")
        )
        self.api_key = (
            api_key
            or os.environ.get("AZURE_OPENAI_API_KEY")
            or os.environ.get("APIM_KEY")
        )
        self.api_version = api_version or os.environ.get(
            "AZURE_OPENAI_API_VERSION", "2025-04-01-preview"
        )
        self.retirement_date = retirement_date
        self.timeout = timeout

    def check(self) -> AzureHealthStatus:
        """Run full health check: retirement guard + endpoint probe."""
        # 1. Retirement guard
        retirement = self._check_retirement()
        if retirement and retirement.status == "retired":
            return retirement

        # 2. Endpoint probe
        if not self.endpoint or not self.api_key:
            return AzureHealthStatus(
                healthy=False,
                status="unhealthy",
                detail="Missing endpoint or API key configuration",
                deployment=self.deployment or "unknown",
            )

        try:
            import time

            start = time.monotonic()
            url = (
                f"{self.endpoint.rstrip('/')}/openai/responses"
                f"?api-version={self.api_version}"
            )
            resp = requests.post(
                url,
                json={
                    "model": self.deployment,
                    "input": "health check ping",
                    "max_output_tokens": 16,
                },
                headers={
                    "Content-Type": "application/json",
                    "api-key": self.api_key,
                },
                timeout=self.timeout,
            )
            latency = (time.monotonic() - start) * 1000

            if resp.status_code == 200:
                status = AzureHealthStatus(
                    healthy=True,
                    status="ok",
                    detail=f"Deployment '{self.deployment}' responsive ({latency:.0f}ms)",
                    deployment=self.deployment or "unknown",
                    latency_ms=latency,
                )
                # Merge retirement warning if applicable
                if retirement and retirement.retirement_days is not None:
                    status.retirement_days = retirement.retirement_days
                    if retirement.status == "degraded":
                        status.status = "degraded"
                        status.detail += f" — retires in {retirement.retirement_days} days"
                return status

            if resp.status_code == 401:
                return AzureHealthStatus(
                    healthy=False,
                    status="unhealthy",
                    detail="Authentication failed (401)",
                    deployment=self.deployment or "unknown",
                    latency_ms=latency,
                )

            if resp.status_code == 404:
                return AzureHealthStatus(
                    healthy=False,
                    status="unhealthy",
                    detail=f"Deployment '{self.deployment}' not found (404)",
                    deployment=self.deployment or "unknown",
                    latency_ms=latency,
                )

            if resp.status_code == 429:
                return AzureHealthStatus(
                    healthy=True,
                    status="degraded",
                    detail=f"Rate limited (429) — {latency:.0f}ms",
                    deployment=self.deployment or "unknown",
                    latency_ms=latency,
                )

            return AzureHealthStatus(
                healthy=False,
                status="unhealthy",
                detail=f"HTTP {resp.status_code} — {resp.text[:200]}",
                deployment=self.deployment or "unknown",
                latency_ms=latency,
            )

        except requests.Timeout:
            return AzureHealthStatus(
                healthy=False,
                status="unreachable",
                detail=f"Timeout after {self.timeout}s",
                deployment=self.deployment or "unknown",
            )
        except requests.ConnectionError:
            return AzureHealthStatus(
                healthy=False,
                status="unreachable",
                detail=f"Connection failed to {self.endpoint}",
                deployment=self.deployment or "unknown",
            )

    def _check_retirement(self) -> AzureHealthStatus | None:
        """Check retirement date. Returns status if retirement is relevant."""
        if not self.retirement_date:
            return None

        try:
            retire_dt = datetime.fromisoformat(self.retirement_date)
            now = datetime.now()
            days_until = (retire_dt - now).days

            if days_until < 0:
                logger.warning(
                    "Azure deployment '%s' PAST retirement (%s)",
                    self.deployment,
                    self.retirement_date,
                )
                return AzureHealthStatus(
                    healthy=False,
                    status="retired",
                    detail=f"Deployment retired on {self.retirement_date}",
                    deployment=self.deployment or "unknown",
                    retirement_days=days_until,
                )

            if days_until <= 30:
                logger.warning(
                    "Azure deployment '%s' retires in %d days",
                    self.deployment,
                    days_until,
                )
                return AzureHealthStatus(
                    healthy=True,
                    status="degraded",
                    detail=f"Retirement in {days_until} days ({self.retirement_date})",
                    deployment=self.deployment or "unknown",
                    retirement_days=days_until,
                )

            return None

        except (ValueError, TypeError):
            return None
