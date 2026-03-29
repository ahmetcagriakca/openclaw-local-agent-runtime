"""Vezir Platform API — FastAPI server.

D-061: FastAPI from day 1.
D-070: Localhost security (Host validation, CORS, 127.0.0.1 binding).
D-074: Startup sequence (config → FS validation → cache warm → normalizer → serve).
"""
import logging
import os
import sys
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from api.capabilities import CapabilityChecker
from api.csrf_middleware import CSRFMiddleware
from api.file_watcher import FileWatcher
from api.normalizer import MissionNormalizer
from api.sse_manager import SSEManager
from utils.atomic_write import atomic_write_json

# ── Paths ────────────────────────────────────────────────────────

# __file__ = agent/api/server.py → dirname×3 = oc root
OC_ROOT = Path(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
MISSIONS_DIR = OC_ROOT / "logs" / "missions"
TELEMETRY_PATH = OC_ROOT / "logs" / "policy-telemetry.jsonl"
CAPABILITIES_PATH = OC_ROOT / "config" / "capabilities.json"
APPROVALS_DIR = OC_ROOT / "logs" / "approvals"
SERVICES_PATH = OC_ROOT / "logs" / "services.json"
API_LOG_PATH = OC_ROOT / "logs" / "mission-control-api.log"

PORT = int(os.environ.get("MCC_PORT", "8003"))

# ── Logging (D-073: 10MB / 5 files / 14 days) ───────────────────

def _setup_logging():
    API_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        str(API_LOG_PATH), maxBytes=10 * 1024 * 1024,
        backupCount=5, encoding="utf-8")
    handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)s %(name)s: %(message)s"))
    logger = logging.getLogger("mcc")
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    return logger

logger = _setup_logging()

# ── Shared State ─────────────────────────────────────────────────

normalizer: MissionNormalizer | None = None
capability_checker: CapabilityChecker | None = None

# ── Services.json (8.13) ────────────────────────────────────────

HEARTBEAT_INTERVAL_S = 30
_service_started_at: str = ""


def _register_service(status: str = "running"):
    """Write/update services.json with heartbeat — GPT Fix 6.

    Atomic read-modify-write: read → update own key → atomic write.
    Heartbeat freshness: lastHeartbeatAt checked for liveness.
    """
    global _service_started_at
    import json as _json

    services = {}
    if SERVICES_PATH.exists():
        try:
            services = _json.loads(
                SERVICES_PATH.read_text(encoding="utf-8"))
        except Exception:
            services = {}

    if not _service_started_at:
        _service_started_at = datetime.now(timezone.utc).isoformat()

    services["mission-control-api"] = {
        "status": status,
        "port": PORT,
        "pid": os.getpid(),
        "startedAt": _service_started_at,
        "lastHeartbeatAt": datetime.now(timezone.utc).isoformat(),
        "heartbeatIntervalS": HEARTBEAT_INTERVAL_S,
    }
    try:
        atomic_write_json(SERVICES_PATH, services)
    except Exception as e:
        logger.warning(f"Failed to write services.json: {e}")


# ── Lifespan (D-074 startup sequence) ───────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    global normalizer, capability_checker

    logger.info("MCC startup: config load")

    # Step 1: FS validation
    MISSIONS_DIR.mkdir(parents=True, exist_ok=True)
    APPROVALS_DIR.mkdir(parents=True, exist_ok=True)
    logger.info("MCC startup: FS validated")

    # Step 2: Cache warm + normalizer init
    normalizer = MissionNormalizer(
        missions_dir=MISSIONS_DIR,
        telemetry_path=TELEMETRY_PATH,
        capabilities_path=CAPABILITIES_PATH,
        approvals_dir=APPROVALS_DIR,
    )
    logger.info("MCC startup: normalizer ready")

    # Step 3: Capability checker
    capability_checker = CapabilityChecker(CAPABILITIES_PATH)
    logger.info("MCC startup: capabilities loaded")

    # Step 4: Register service
    _register_service("running")
    logger.info(f"MCC startup: serving on 127.0.0.1:{PORT}")
    # D-097: Legacy dashboard removed in Sprint 13. Vezir UI on :3000 is primary.

    # Step 5: Start heartbeat background task (GPT Fix 6)
    import asyncio
    heartbeat_task = asyncio.create_task(_heartbeat_loop())

    # Step 6: Mission Scheduler (D-120 / B-101)
    from schedules.scheduler import MissionScheduler
    from schedules.store import ScheduleStore
    schedule_store = ScheduleStore()
    scheduler = MissionScheduler(schedule_store, MISSIONS_DIR)
    await scheduler.start()
    app.state.scheduler = scheduler
    logger.info("MCC startup: scheduler ready")

    # Step 7: FileWatcher + SSE Manager (Sprint 10)
    event_queue: asyncio.Queue = asyncio.Queue(maxsize=200)
    file_watcher = FileWatcher(
        missions_dir=MISSIONS_DIR,
        telemetry_path=TELEMETRY_PATH,
        capabilities_path=CAPABILITIES_PATH,
        services_path=SERVICES_PATH,
        approvals_dir=APPROVALS_DIR,
        event_queue=event_queue,
    )
    sse_manager = SSEManager()
    app.state.sse_manager = sse_manager

    await file_watcher.start()
    await sse_manager.start_heartbeat()
    await sse_manager.start_watcher_bridge(event_queue)
    logger.info("MCC startup: SSE + FileWatcher ready")

    yield

    # Shutdown
    await scheduler.stop()
    await file_watcher.stop()
    await sse_manager.shutdown()
    heartbeat_task.cancel()
    try:
        await heartbeat_task
    except asyncio.CancelledError:
        pass
    _register_service("stopped")
    logger.info("MCC shutdown")


async def _heartbeat_loop():
    """GPT Fix 6: Periodic heartbeat update to services.json."""
    import asyncio
    while True:
        await asyncio.sleep(HEARTBEAT_INTERVAL_S)
        try:
            _register_service("running")
        except Exception as e:
            logger.warning(f"Heartbeat failed: {e}")


# ── App ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Vezir Platform",
    version="1.0.0",
    lifespan=lifespan,
)

# D-070: CORS — only localhost:3000 (React dev)
# Sprint 11: POST added for mutation endpoints
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ],
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

# D-089: CSRF — Origin header validation for POST requests
app.add_middleware(CSRFMiddleware)

# B-005: Request throttling — per-IP sliding window
from api.throttle import ThrottleMiddleware

app.add_middleware(ThrottleMiddleware)

# B-012: Idempotency key middleware for mutation requests
from api.idempotency import IdempotencyMiddleware

app.add_middleware(IdempotencyMiddleware)


# D-070: Host header validation middleware
@app.middleware("http")
async def validate_host(request: Request, call_next):
    host = request.headers.get("host", "")
    allowed = {"localhost", "127.0.0.1",
               f"localhost:{PORT}", f"127.0.0.1:{PORT}",
               "testserver"}  # FastAPI TestClient
    if host not in allowed:
        logger.warning("Host validation rejected: %s %s (host=%s)",
                       request.method, request.url.path, host)
        return JSONResponse(
            status_code=403,
            content={"error": "forbidden", "detail": "Invalid Host header"},
        )
    response = await call_next(request)
    # Log 4xx/5xx errors
    if response.status_code >= 400:
        logger.warning("HTTP %s %s %s → %d",
                       request.method, request.url.path,
                       request.client.host if request.client else "?",
                       response.status_code)
    return response


# ── Import routers ──────────────────────────────────────────────

from api.alerts_api import router as alerts_router
from api.approval_api import router as approval_router
from api.approval_mutation_api import router as approval_mutation_router
from api.dashboard_api import router as dashboard_router
from api.health_api import router as health_router
from api.logs_api import router as logs_router
from api.mission_api import router as mission_router
from api.mission_create_api import router as mission_create_router
from api.mission_mutation_api import router as mission_mutation_router
from api.roles_api import router as roles_router
from api.schedules_api import router as schedules_router
from api.signal_api import router as signal_router
from api.sse_api import router as sse_router
from api.telemetry_api import router as telemetry_router
from api.telemetry_query_api import router as telemetry_query_router
from api.templates_api import router as templates_router

app.include_router(mission_router, prefix="/api/v1")
app.include_router(approval_router, prefix="/api/v1")
app.include_router(telemetry_router, prefix="/api/v1")
app.include_router(health_router, prefix="/api/v1")
app.include_router(sse_router, prefix="/api/v1")
app.include_router(approval_mutation_router, prefix="/api/v1")
app.include_router(mission_mutation_router, prefix="/api/v1")
app.include_router(mission_create_router, prefix="/api/v1")
app.include_router(signal_router, prefix="/api/v1")
app.include_router(logs_router, prefix="/api/v1")
app.include_router(roles_router, prefix="/api/v1")
app.include_router(dashboard_router, prefix="/api/v1")
app.include_router(telemetry_query_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(templates_router, prefix="/api/v1")
app.include_router(schedules_router, prefix="/api/v1")


# ── TLS Configuration (D-130) ───────────────────────────────────

def _get_tls_config() -> dict:
    """Get TLS configuration per D-130.

    Default mode: TLS required (fail-closed). Missing cert = startup deny.
    Dev mode (--dev or VEZIR_DEV=1): HTTP fallback with warning.
    """
    import ssl
    cert_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config", "tls", "server.pem"
    )
    key_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
        "config", "tls", "server-key.pem"
    )

    dev_mode = os.environ.get("VEZIR_DEV", "") == "1" or "--dev" in sys.argv

    if os.path.exists(cert_path) and os.path.exists(key_path):
        return {
            "ssl_certfile": cert_path,
            "ssl_keyfile": key_path,
            "ssl_version": ssl.TLSVersion.TLSv1_2,
        }

    if dev_mode:
        logger.warning("TLS cert not found — running HTTP in dev mode (INSECURE)")
        return {}

    logger.error("TLS cert not found and not in dev mode — refusing to start (D-130)")
    sys.exit(1)


# ── HSTS Middleware (D-130) ─────────────────────────────────────

@app.middleware("http")
async def hsts_middleware(request, call_next):
    """Add HSTS header when TLS is active (D-130)."""
    response = await call_next(request)
    if request.url.scheme == "https":
        response.headers["Strict-Transport-Security"] = "max-age=31536000"
    return response


# ── Main ────────────────────────────────────────────────────────

def main():
    import uvicorn
    tls_config = _get_tls_config()
    uvicorn.run(
        "api.server:app",
        host="127.0.0.1",
        port=PORT,
        log_level="info",
        **tls_config,
    )


if __name__ == "__main__":
    import sys
    main()
