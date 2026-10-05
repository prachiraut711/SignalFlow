"""
Event Ingestion & Exploration API Endpoints
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.db.duckdb import DuckDBService, get_duckdb_service
from app.schemas.event import EventCreate, EventResponse, EventItem
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


@router.get(
    "",
    response_model=List[EventItem],
    summary="List ingested events",
    description="Retrieve ingested events from the analytical store with optional filtering."
)
@router.get(
    "/",
    response_model=List[EventItem],
    include_in_schema=False
)
def list_events(
    service: Optional[str] = Query(None, description="Filter by service name"),
    event_type: Optional[str] = Query(None, description="Filter by event type"),
    region: Optional[str] = Query(None, description="Filter by region"),
    status_code: Optional[int] = Query(None, description="Filter by HTTP status code"),
    limit: int = Query(50, ge=1, le=500, description="Maximum events to return"),
    offset: int = Query(0, ge=0, description="Offset for pagination"),
    duckdb_svc: DuckDBService = Depends(get_duckdb_service),
) -> List[EventItem]:
    """
    Query processed analytical events for the Event Explorer.
    """
    conditions = []
    params = []
    if service:
        conditions.append("service = ?")
        params.append(service)
    if event_type:
        conditions.append("event_type = ?")
        params.append(event_type)
    if region:
        conditions.append("region = ?")
        params.append(region)
    if status_code:
        conditions.append("status_code = ?")
        params.append(status_code)

    where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""
    query = f"""
    SELECT event_id, timestamp, service, event_type, region, status_code, latency_ms, value, user_id, ingested_at
    FROM events
    {where_clause}
    ORDER BY timestamp DESC
    LIMIT ? OFFSET ?
    """
    params.extend([limit, offset])
    rows = duckdb_svc.query(query, tuple(params))
    items = []
    for r in rows:
        items.append(
            EventItem(
                event_id=str(r[0]),
                timestamp=r[1],
                service=str(r[2]),
                event_type=str(r[3]),
                region=str(r[4]),
                status_code=int(r[5]),
                latency_ms=float(r[6]),
                value=float(r[7] or 0.0),
                user_id=str(r[8]) if r[8] else None,
                ingested_at=r[9],
            )
        )
    return items
