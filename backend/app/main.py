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
from app.services.redis_service import get_redis_service
from app.db.postgres import init_db

settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage application startup and shutdown lifecycle."""
    # Attempt to initialize relational schema (anomalies, signals, signal_anomalies tables)
    init_db()
    yield
    # Graceful shutdown of Redis client pool
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
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
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
