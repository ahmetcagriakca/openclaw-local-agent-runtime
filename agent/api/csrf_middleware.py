"""CSRF Middleware — D-089: SameSite=Strict + Origin Header Check.

Applied to POST requests only. Rejects requests without valid localhost Origin → 403.
Localhost single-operator system (D-070 extension).
"""
import logging

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("mcc.csrf")

# D-089: Allowed origins — localhost only (D-070)
ALLOWED_ORIGINS = {
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8003",
    "http://127.0.0.1:8003",
}


class CSRFMiddleware(BaseHTTPMiddleware):
    """Origin header validation for POST requests (D-089).

    - GET requests: pass through (read-only)
    - POST requests: Origin header must be present and in ALLOWED_ORIGINS
    - Missing or invalid Origin → 403
    """

    async def dispatch(self, request: Request, call_next):
        if request.method == "POST":
            origin = request.headers.get("origin", "")
            if not origin or origin not in ALLOWED_ORIGINS:
                logger.warning(
                    "CSRF reject: method=%s path=%s origin=%s",
                    request.method, request.url.path, origin or "(missing)",
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "error": "forbidden",
                        "detail": "Missing or invalid Origin header",
                    },
                )
        return await call_next(request)
