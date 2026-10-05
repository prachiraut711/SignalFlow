"""
Health Check API Endpoints
"""

from fastapi import APIRouter
from app.schemas.health import HealthResponse

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    Health check endpoint returning system status.
    """
    return HealthResponse(
        status="healthy",
        service="signalflow-backend"
    )
