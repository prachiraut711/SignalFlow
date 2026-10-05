"""
Pydantic Schemas for Signal Correlation & Incident Lifecycle
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field

from app.schemas.anomaly import AnomalyResponse


class SignalStatus(str, Enum):
    """Lifecycle status of an operational signal."""
    OPEN = "OPEN"
    RESOLVED = "RESOLVED"


class SignalSeverity(str, Enum):
    """Aggregated incident severity levels."""
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class SignalResponse(BaseModel):
    """Standard representation of an operational incident signal."""
    id: int
    signal_key: str
    title: str
    description: str
    severity: SignalSeverity
    service: str
    region: str
    status: SignalStatus
    first_detected_at: datetime
    last_detected_at: datetime
    created_at: datetime
    updated_at: datetime
    related_anomalies_count: int = Field(default=0)

    model_config = {"from_attributes": True}


class SignalDetailResponse(SignalResponse):
    """Detailed signal representation including all correlated raw anomalies."""
    anomalies: List[AnomalyResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class SignalCorrelationResponse(BaseModel):
    """Response payload returned by the correlation engine."""
    signals_created: int
    signals_updated: int
    anomalies_correlated: int
    signals: List[SignalResponse] = Field(default_factory=list)
