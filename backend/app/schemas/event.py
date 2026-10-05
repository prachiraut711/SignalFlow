"""
Event Schemas and Data Models for SignalFlow Pipeline
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator


class EventType(str, Enum):
    """Supported business and application event types."""
    USER_SIGNUP = "user_signup"
    USER_LOGIN = "user_login"
    ORDER_CREATED = "order_created"
    ORDER_CANCELLED = "order_cancelled"
    PAYMENT_SUCCESS = "payment_success"
    PAYMENT_FAILED = "payment_failed"
    REFUND_CREATED = "refund_created"
    API_REQUEST = "api_request"
    API_ERROR = "api_error"
    FILE_UPLOAD = "file_upload"
    NOTIFICATION_SENT = "notification_sent"


class EventCreate(BaseModel):
    """
    Incoming event payload validation schema.
    """
    timestamp: datetime = Field(
        description="ISO-8601 formatted event occurrence timestamp"
    )
    service: str = Field(
        ...,
        min_length=1,
        max_length=100,
        description="Originating service identifier (e.g. payment-service)"
    )
    event_type: EventType = Field(
        ...,
        description="Type of the business or technical event"
    )
    region: str = Field(
        default="global",
        min_length=1,
        max_length=100,
        description="Geographic region / datacenter (e.g. Pune, us-east-1)"
    )
    status_code: int = Field(
        ...,
        ge=100,
        le=599,
        description="HTTP-style response or operation status code (100-599)"
    )
    latency_ms: float = Field(
        ...,
        ge=0.0,
        description="Duration of the event operation in milliseconds (>= 0)"
    )
    value: Optional[float] = Field(
        default=0.0,
        description="Optional business monetary or transaction value (e.g. 1499.0)"
    )
    user_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Identifier of the user associated with the event"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Arbitrary supplementary contextual metadata"
    )

    @field_validator("service", "region", mode="before")
    @classmethod
    def strip_and_validate_non_empty(cls, v: Any) -> str:
        if isinstance(v, str):
            v_stripped = v.strip()
            if not v_stripped:
                raise ValueError("Value cannot be blank or whitespace-only")
            return v_stripped
        return v


class EventRecord(EventCreate):
    """
    Internal event schema enriched with server-assigned event ID and ingestion timestamp.
    """
    event_id: str = Field(..., description="Unique server-generated event identifier")
    ingested_at: datetime = Field(..., description="Server timestamp when event was queued")


class EventResponse(BaseModel):
    """
    Response returned to client upon successful ingestion.
    """
    success: bool = True
    message: str = "Event accepted"
    event_id: str


class EventItem(BaseModel):
    """
    Normalized event item schema returned by GET /api/events for exploration.
    """
    event_id: str
    timestamp: datetime
    service: str
    event_type: str
    region: str
    status_code: int
    latency_ms: float
    value: Optional[float] = 0.0
    user_id: Optional[str] = None
    ingested_at: datetime
