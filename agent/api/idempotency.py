"""Mutation idempotency key middleware — B-012.

Prevents duplicate mutation execution via Idempotency-Key header.
Same key + same request = cached response (no re-execution).
Same key + different body = 422 error.
No key = normal execution (backward compatible).
TTL: 24 hours.
"""
import hashlib
import logging
import time
from dataclasses import dataclass

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger("mcc.idempotency")

IDEMPOTENCY_HEADER = "Idempotency-Key"
TTL_SECONDS = 86400  # 24 hours
MUTATION_METHODS = {"POST", "PUT", "DELETE"}


@dataclass
class CachedResponse:
    status_code: int
    body: bytes
    body_hash: str
    created_at: float


class IdempotencyMiddleware(BaseHTTPMiddleware):
    """Idempotency key middleware for mutation endpoints."""

    def __init__(self, app):
        super().__init__(app)
        self._cache: dict[str, CachedResponse] = {}

    def _cleanup(self) -> None:
        """Remove expired entries."""
        now = time.time()
        expired = [k for k, v in self._cache.items() if now - v.created_at > TTL_SECONDS]
        for k in expired:
            del self._cache[k]

    async def dispatch(self, request: Request, call_next):
        # Only apply to mutation methods
        if request.method not in MUTATION_METHODS:
            return await call_next(request)

        # Check for idempotency key
        idem_key = request.headers.get(IDEMPOTENCY_HEADER)
        if not idem_key:
            return await call_next(request)

        # Periodic cleanup
        if len(self._cache) > 1000:
            self._cleanup()

        # Hash the request body for mismatch detection
        body = await request.body()
        body_hash = hashlib.sha256(body).hexdigest()[:16]

        # Scope key by client identity
        client_ip = request.client.host if request.client else "unknown"
        cache_key = f"{client_ip}:{idem_key}"

        # Check cache
        if cache_key in self._cache:
            cached = self._cache[cache_key]

            # Check for body mismatch (same key, different request)
            if cached.body_hash != body_hash:
                logger.warning("Idempotency key reuse with different body: %s", idem_key)
                return JSONResponse(
                    status_code=422,
                    content={"detail": "Idempotency key already used with a different request body."},
                )

            # Return cached response
            logger.info("Idempotency cache hit: %s", idem_key)
            return Response(
                content=cached.body,
                status_code=cached.status_code,
                media_type="application/json",
            )

        # Execute request and cache response
        response = await call_next(request)

        # Read response body for caching
        response_body = b""
        async for chunk in response.body_iterator:
            response_body += chunk

        # Cache the response
        self._cache[cache_key] = CachedResponse(
            status_code=response.status_code,
            body=response_body,
            body_hash=body_hash,
            created_at=time.time(),
        )

        return Response(
            content=response_body,
            status_code=response.status_code,
            media_type=response.media_type,
            headers=dict(response.headers),
        )
