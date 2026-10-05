"""
Analytics API Endpoints

Provides read-only access to platform aggregate metrics, service-level health,
and time-windowed event rollups stored in DuckDB.
"""

from typing import List
from fastapi import APIRouter, Depends
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    ServiceMetricItem,
    TimeWindowMetricItem,
)
from app.services.analytics_service import AnalyticsService, get_analytics_service

router = APIRouter(prefix="/analytics", tags=["Analytics"])


@router.get(
    "/overview",
    response_model=AnalyticsOverviewResponse,
    summary="Get platform overview metrics",
    description="Returns global event counts, total errors, overall error rate, and average latency."
)
async def get_overview(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> AnalyticsOverviewResponse:
    """Compute and return global platform metrics."""
    return analytics_service.get_overview()


@router.get(
    "/services",
    response_model=List[ServiceMetricItem],
    summary="Get per-service metrics",
    description="Returns aggregated event volumes, error counts, error rates, and latencies grouped by service."
)
async def get_service_metrics(
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> List[ServiceMetricItem]:
    """Compute and return metrics broken down by individual microservice."""
    return analytics_service.get_service_metrics()


@router.get(
    "/windows",
    response_model=List[TimeWindowMetricItem],
    summary="Get 1-minute time window metrics",
    description="Returns aggregated metrics bucketed into 1-minute intervals for trend analysis."
)
async def get_time_window_metrics(
    window_minutes: int = 1,
    analytics_service: AnalyticsService = Depends(get_analytics_service)
) -> List[TimeWindowMetricItem]:
    """Return time-windowed aggregation buckets."""
    return analytics_service.get_time_window_metrics(window_minutes=window_minutes)
