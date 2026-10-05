"""
Health Check API Endpoints
"""

from fastapi import APIRouter, Depends, Response, status
from app.schemas.health import HealthResponse
from app.services.redis_service import RedisService, get_redis_service

router = APIRouter(tags=["Health"])


@router.get("/health", response_model=HealthResponse, response_model_exclude_none=True)
async def health_check() -> HealthResponse:
    """
    Standard backend service health check endpoint.
    Remains operational regardless of external dependencies.
    """
    return HealthResponse(
        status="healthy",
        service="signalflow-backend"
    )


@router.get("/health/redis", response_model=HealthResponse, response_model_exclude_none=True)
async def redis_health_check(
    response: Response,
    redis_service: RedisService = Depends(get_redis_service)
) -> HealthResponse:
    """
    Check connectivity to the Redis Stream buffer instance.
    """
    is_alive = await redis_service.ping()
    if is_alive:
        return HealthResponse(
            status="healthy",
            service="redis"
        )
    
    response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return HealthResponse(
        status="unhealthy",
        service="redis",
        detail="Redis server is unreachable or not responding"
    )
