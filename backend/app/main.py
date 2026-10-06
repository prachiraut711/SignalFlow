"""
SignalFlow FastAPI Application Entrypoint
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.api.health import router as health_router
from app.api.events import router as events_router
from app.api.analytics import router as analytics_router
from app.api.anomalies import router as anomalies_router
from app.api.signals import router as signals_router
from app.api.ai import router as ai_router
from app.api.simulator import router as simulator_router
from app.services.redis_service import get_redis_service
from app.db.postgres import init_db

import asyncio
import logging

logger = logging.getLogger("SignalFlowApp")
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # 1. Attempt to initialize relational schema (anomalies, signals, signal_anomalies tables)
    init_db()

    # 2. Optionally run background worker in-process (for Render free single-service deployment)
    worker_task = None
    worker = None
    worker_stop_event = None

    if settings.EMBED_WORKER:
        from app.workers.event_worker import EventWorker
        worker = EventWorker()
        worker_stop_event = asyncio.Event()
        worker_task = asyncio.create_task(worker.run(stop_event=worker_stop_event))
        logger.info("Embedded EventWorker background task started within FastAPI lifespan")

    yield

    # 3. Graceful shutdown of embedded worker
    if worker and worker_task:
        worker.stop()
        if worker_stop_event:
            worker_stop_event.set()
        try:
            await asyncio.wait_for(worker_task, timeout=3.0)
        except (asyncio.TimeoutError, asyncio.CancelledError):
            pass
        logger.info("Embedded EventWorker stopped")

    # 4. Graceful shutdown of Redis client pool
    redis_service = get_redis_service()
    await redis_service.close()


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Business Event Intelligence & Anomaly Detection Platform",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Configure CORS for frontend access
cors_origins = set(settings.CORS_ORIGINS)
if settings.FRONTEND_URL:
    url_cleaned = settings.FRONTEND_URL.strip().rstrip("/")
    if url_cleaned:
        cors_origins.add(url_cleaned)
        cors_origins.add(f"{url_cleaned}/")

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", tags=["Root"])
async def root():
    """Root endpoint welcoming clients and referencing documentation."""
    return {
        "message": "Welcome to SignalFlow API",
        "docs": "/docs",
        "health": "/health",
        "redis_health": "/health/redis",
        "events_api": "/api/events",
        "analytics_api": "/api/analytics/overview",
        "anomalies_api": "/api/anomalies",
        "signals_api": "/api/signals",
        "status": "operational",
    }


# Health check endpoints (/health and /health/redis)
app.include_router(health_router)
app.include_router(health_router, prefix="/api/v1")

# Mount Event Ingestion router under /api as well as /api/v1
app.include_router(events_router, prefix="/api")
app.include_router(events_router, prefix="/api/v1")

# Mount Analytics query router under /api as well as /api/v1
app.include_router(analytics_router, prefix="/api")
app.include_router(analytics_router, prefix="/api/v1")

# Mount Anomalies router under /api as well as /api/v1
app.include_router(anomalies_router, prefix="/api")
app.include_router(anomalies_router, prefix="/api/v1")

# Mount Signals router under /api as well as /api/v1
app.include_router(signals_router, prefix="/api")
app.include_router(signals_router, prefix="/api/v1")

# Mount AI Explanation router under /api as well as /api/v1
app.include_router(ai_router, prefix="/api")
app.include_router(ai_router, prefix="/api/v1")

# Mount Simulator router under /api as well as /api/v1
app.include_router(simulator_router, prefix="/api")
app.include_router(simulator_router, prefix="/api/v1")


if __name__ == "__main__":
    import os
    import uvicorn

    server_port = int(os.getenv("PORT", settings.PORT))
    server_host = os.getenv("HOST", settings.HOST)
    uvicorn.run("app.main:app", host=server_host, port=server_port, reload=False)


