"""
Event Ingestion API Endpoints
"""

from fastapi import APIRouter, Depends, status
from app.schemas.event import EventCreate, EventResponse
from app.services.event_service import EventService, get_event_service

router = APIRouter(prefix="/events", tags=["Events"])


@router.post(
    "",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest application event",
    description="Validates incoming business telemetry and enqueues to Redis Stream for processing."
)
@router.post(
    "/",
    response_model=EventResponse,
    status_code=status.HTTP_201_CREATED,
    include_in_schema=False
)
async def ingest_event(
    event: EventCreate,
    event_service: EventService = Depends(get_event_service),
) -> EventResponse:
    """
    Ingest a single event into the SignalFlow stream pipeline.
    """
    return await event_service.ingest_event(event)
