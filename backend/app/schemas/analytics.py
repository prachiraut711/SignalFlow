"""
Pydantic Schemas for Analytics and Aggregated Telemetry Metrics
"""

from datetime import datetime
from typing import List, Optional
from pydantic import BaseModel, Field


class AnalyticsOverviewResponse(BaseModel):
    """Overall platform aggregate metrics."""
    total_events: int = Field(default=0, description="Total number of processed events")
    total_errors: int = Field(default=0, description="Total number of failed or error events")
    error_rate: float = Field(default=0.0, description="Percentage of error events (0.0 to 100.0)")
    average_latency_ms: float = Field(default=0.0, description="Mean latency across all events in milliseconds")


class ServiceMetricItem(BaseModel):
    """Per-service aggregate metrics."""
    service: str = Field(..., description="Service identifier name")
    event_count: int = Field(..., description="Number of events recorded for this service")
    error_count: int = Field(..., description="Number of error/failure events for this service")
    error_rate: float = Field(..., description="Error rate percentage (0.0 to 100.0)")
    average_latency_ms: float = Field(..., description="Average processing latency in milliseconds")


class TimeWindowMetricItem(BaseModel):
    """1-minute aggregated metrics bucket."""
    time_window: datetime = Field(..., description="Start timestamp of the 1-minute aggregation window")
    service: str = Field(..., description="Service identifier")
    event_type: str = Field(..., description="Type of event")
    event_count: int = Field(..., description="Event count in this window")
    error_count: int = Field(..., description="Error count in this window")
    success_count: int = Field(..., description="Success count in this window")
    error_rate: float = Field(..., description="Error rate percentage in this window")
    average_latency_ms: float = Field(..., description="Average latency in this window")
