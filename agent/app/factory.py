"""Application factory — D-104.

Wraps the existing api.server:app as a factory function.
This is a thin adapter over the existing server module,
not a rewrite. Full route migration happens in 14.20.
"""
from __future__ import annotations

import os
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from fastapi import FastAPI


def create_app(testing: bool = False) -> FastAPI:
    """Create and return the FastAPI application.

    Args:
        testing: If True, skip file watcher and heartbeat.

    Returns:
        Configured FastAPI app instance.
    """
    # Import the existing app from current location
    from api.server import app
    return app


def get_config() -> dict:
    """Return application configuration from environment."""
    return {
        "port": int(os.environ.get("VEZIR_API_PORT", "8003")),
        "host": os.environ.get("VEZIR_API_HOST", "127.0.0.1"),
        "log_level": os.environ.get("VEZIR_LOG_LEVEL", "info"),
        "missions_dir": os.environ.get("VEZIR_MISSIONS_DIR", ""),
    }
