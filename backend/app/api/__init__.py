"""
API Routes Package
"""

from fastapi import APIRouter
from app.api.health import router as health_router
from app.api.events import router as events_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(events_router)

__all__ = ["api_router", "health_router", "events_router"]
