"""
API Routes Package
"""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.events import router as events_router
from app.api.analytics import router as analytics_router
from app.api.anomalies import router as anomalies_router
from app.api.signals import router as signals_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(events_router)
api_router.include_router(analytics_router)
api_router.include_router(anomalies_router)
api_router.include_router(signals_router)

__all__ = [
    "api_router",
    "health_router",
    "events_router",
    "analytics_router",
    "anomalies_router",
    "signals_router",
]
