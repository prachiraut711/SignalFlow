"""
Pydantic Schemas for Anomaly Detection Results & API Responses
"""

from datetime import datetime
from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class SeverityLevel(str, Enum):
    """Anomaly severity classification tiers."""
    INFO = "INFO"
    WARNING = "WARNING"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AnomalyResponse(BaseModel):
    """Public anomaly representation schema."""
    id: Optional[int] = None
    service: str
    region: str = "global"
    metric: str
    anomaly_type: str
    current_value: float
    baseline_value: float
    percentage_change: float
    z_score: Optional[float] = None
    isolation_score: Optional[float] = None
    severity: SeverityLevel
    detected_at: datetime
    time_window: datetime
    reason: str

    model_config = {"from_attributes": True}


class DetectionRunResponse(BaseModel):
    """Summary of an executed anomaly detection run."""
    windows_evaluated: int
    anomalies_detected: int
    anomalies_persisted: int
    anomalies: List[AnomalyResponse] = Field(default_factory=list)
