"""RFC 9457 Error Envelope — standardized API error responses.

Sprint 50: Structured error model with type, title, status, detail, instance.
Global exception handler wraps HTTPException into RFC 9457 format.
Backward compatible — keeps 'detail' field for existing clients.
"""

import logging
from datetime import datetime, timezone
from enum import Enum

from fastapi import FastAPI, Request
from fastapi.exceptions import HTTPException, RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger("mcc.api.error")


class ErrorCode(str, Enum):
    """Standard error codes for API responses."""
    NOT_FOUND = "not_found"
    VALIDATION_ERROR = "validation_error"
    CONFLICT = "conflict"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"
    FORBIDDEN = "forbidden"
    INTERNAL = "internal_error"
    BAD_REQUEST = "bad_request"


# Map HTTP status codes to error codes
_STATUS_TO_CODE = {
    400: ErrorCode.BAD_REQUEST,
    401: ErrorCode.UNAUTHORIZED,
    403: ErrorCode.FORBIDDEN,
    404: ErrorCode.NOT_FOUND,
    409: ErrorCode.CONFLICT,
    422: ErrorCode.VALIDATION_ERROR,
    429: ErrorCode.RATE_LIMITED,
}


def _build_error_response(
    status: int,
    detail: str,
    error_code: str | None = None,
    instance: str | None = None,
) -> dict:
    """Build RFC 9457 error envelope."""
    code = error_code or _STATUS_TO_CODE.get(status, ErrorCode.INTERNAL).value
    return {
        "type": f"about:blank#{code}",
        "title": code.replace("_", " ").title(),
        "status": status,
        "detail": detail,
        "instance": instance or "",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def register_error_handlers(app: FastAPI) -> None:
    """Register global exception handlers for RFC 9457 error envelope."""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        body = _build_error_response(
            status=exc.status_code,
            detail=str(exc.detail),
            instance=str(request.url.path),
        )
        logger.warning(
            "API error %d %s: %s (path=%s)",
            exc.status_code, body["title"], exc.detail, request.url.path,
        )
        return JSONResponse(status_code=exc.status_code, content=body)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        detail = "; ".join(
            f"{'.'.join(str(loc) for loc in e['loc'])}: {e['msg']}"
            for e in exc.errors()
        )
        body = _build_error_response(
            status=422,
            detail=detail,
            error_code=ErrorCode.VALIDATION_ERROR.value,
            instance=str(request.url.path),
        )
        logger.warning("Validation error: %s (path=%s)", detail, request.url.path)
        return JSONResponse(status_code=422, content=body)

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        """Catch-all: prevent stack trace leakage to clients (CodeQL py/stack-trace-exposure)."""
        logger.exception("Unhandled error on %s", request.url.path)
        body = _build_error_response(
            status=500,
            detail="Internal server error",
            error_code=ErrorCode.INTERNAL.value,
            instance=str(request.url.path),
        )
        return JSONResponse(status_code=500, content=body)
