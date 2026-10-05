"""
SignalFlow FastAPI Application Entrypoint
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.schemas.health import HealthResponse
from app.api import api_router

settings = get_settings()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Business Event Intelligence & Anomaly Detection Platform",
    docs_url="/docs",
    redoc_url="/redoc",
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
        "status": "operational",
    }


@app.get("/health", tags=["Health"], response_model=HealthResponse)
async def health() -> HealthResponse:
    """
    Standard health check endpoint.
    Returns status and service identification.
    """
    return HealthResponse(
        status="healthy",
        service="signalflow-backend"
    )


# Mount versioned API routes for future endpoints (e.g. /api/v1)
app.include_router(api_router, prefix="/api/v1")
