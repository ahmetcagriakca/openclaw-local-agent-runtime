"""API request throttling — B-005.

Sliding window per-IP throttling middleware.
Default: 100 req/min GET, 20 req/min POST mutations.
Health endpoint exempt.
"""
import logging
import time
from collections import defaultdict

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("mcc.throttle")

# Default limits (requests per minute)
GET_LIMIT = 100
MUTATION_LIMIT = 20
WINDOW_SECONDS = 60

# Disable in test environment
import os

_TESTING = os.environ.get("TESTING", "") == "1" or "pytest" in os.environ.get("_", "")

# Exempt paths
EXEMPT_PATHS = {"/api/v1/health"}


class ThrottleMiddleware(BaseHTTPMiddleware):
    """Sliding window request throttling per client IP."""

    def __init__(self, app, get_limit: int = GET_LIMIT, mutation_limit: int = MUTATION_LIMIT):
        super().__init__(app)
        self.get_limit = get_limit
        self.mutation_limit = mutation_limit
        self._requests: dict[str, list[float]] = defaultdict(list)

    def _get_client_ip(self, request: Request) -> str:
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _clean_window(self, key: str, now: float) -> None:
        cutoff = now - WINDOW_SECONDS
        self._requests[key] = [t for t in self._requests[key] if t > cutoff]

    async def dispatch(self, request: Request, call_next):
        # Skip throttling in test mode
        if _TESTING:
            return await call_next(request)

        path = request.url.path
        method = request.method

        # Exempt paths
        if path in EXEMPT_PATHS:
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        now = time.time()

        # Determine limit based on method
        if method in ("POST", "PUT", "DELETE"):
            limit = self.mutation_limit
            key = f"{client_ip}:mutation"
        else:
            limit = self.get_limit
            key = f"{client_ip}:read"

        # Clean old entries
        self._clean_window(key, now)

        # Check limit
        if len(self._requests[key]) >= limit:
            retry_after = int(WINDOW_SECONDS - (now - self._requests[key][0])) + 1
            logger.warning("Throttled %s %s from %s (%d/%d)", method, path, client_ip, len(self._requests[key]), limit)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please retry later."},
                headers={"Retry-After": str(retry_after)},
            )

        # Record request
        self._requests[key].append(now)
        return await call_next(request)
