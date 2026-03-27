"""API v1 routers — re-exports from current api/ modules.

This is a compatibility shim. Routers are imported from their
current locations in agent/api/ and re-exported here so new code
can import from app.api.v1.
"""
from api.approval_api import router as approvals_router
from api.approval_mutation_api import router as approval_mutation_router
from api.health_api import router as health_router
from api.logs_api import router as logs_router
from api.mission_api import router as missions_router
from api.mission_create_api import router as mission_create_router
from api.mission_mutation_api import router as mutations_router
from api.roles_api import router as roles_router
from api.signal_api import router as signals_router
from api.sse_api import router as events_router
from api.telemetry_api import router as telemetry_router

__all__ = [
    "missions_router", "roles_router", "health_router",
    "approvals_router", "events_router", "mutations_router",
    "telemetry_router", "logs_router", "signals_router",
    "mission_create_router", "approval_mutation_router",
]
