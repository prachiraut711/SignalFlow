"""
Event Ingestion Service Module

Coordinates server-side event enrichment, unique event ID generation,
JSON serialization, and pushing to Redis Streams buffer.
"""

from datetime import datetime, timezone
import logging
import uuid
from typing import Optional
from fastapi import Depends, HTTPException, status

from app.config import get_settings
from app.schemas.event import EventCreate, EventRecord, EventResponse
from app.services.redis_service import RedisService, get_redis_service

logger = logging.getLogger(__name__)


class EventService:
    """
    Business service managing incoming event enrichment and buffering.
    """

    def __init__(self, redis_service: Optional[RedisService] = None):
        self.settings = get_settings()
        self.redis_service = redis_service or get_redis_service()

    def generate_event_id(self) -> str:
        """Generate a collision-resistant unique event identifier."""
        return f"evt_{uuid.uuid4().hex}"

    async def ingest_event(self, event_create: EventCreate) -> EventResponse:
        """
        Enrich validated event with server-generated ID and queue in Redis Stream.

        Args:
            event_create: Validated incoming Pydantic event schema

        Returns:
            EventResponse indicating successful ingestion and assigned event_id
        """
        event_id = self.generate_event_id()
        ingested_at = datetime.now(timezone.utc)

        # Build full event record containing server ID and timestamp
        event_record = EventRecord(
            event_id=event_id,
            ingested_at=ingested_at,
            **event_create.model_dump()
        )

        # Prepare stream dictionary for Redis XADD
        stream_payload = {
            "event_id": event_id,
            "service": event_create.service,
            "event_type": str(event_create.event_type.value),
            "status_code": event_create.status_code,
            "payload": event_record.model_dump_json(),
        }

        try:
            redis_msg_id = await self.redis_service.add_to_stream(
                stream_name=self.settings.REDIS_STREAM_NAME,
                fields=stream_payload,
            )
            logger.info(
                f"Queued event {event_id} ({event_create.event_type.value}) "
                f"to stream '{self.settings.REDIS_STREAM_NAME}' with redis_id={redis_msg_id}"
            )
        except Exception as exc:
            logger.error(f"Failed to queue event {event_id} to Redis Stream: {exc}")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Event stream buffer is temporarily unavailable: {exc}",
            )

        return EventResponse(
            success=True,
            message="Event accepted",
            event_id=event_id,
        )


def get_event_service(
    redis_service: RedisService = Depends(get_redis_service)
) -> EventService:
    """Dependency provider returning an EventService configured with RedisService."""
    return EventService(redis_service=redis_service)
