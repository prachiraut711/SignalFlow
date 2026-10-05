"""
Simulator Schemas and Request/Response Models
"""

from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field


class SimulationScenario(str, Enum):
    """Supported simulation scenarios for demonstrating platform observability."""
    NORMAL_TRAFFIC = "normal_traffic"
    PAYMENT_FAILURE_SPIKE = "payment_failure_spike"
    API_ERROR_SPIKE = "api_error_spike"
    HIGH_LATENCY = "high_latency"
    TRAFFIC_SURGE = "traffic_surge"
    REGIONAL_FAILURE = "regional_failure"


class SimulatorStartRequest(BaseModel):
    """
    Configuration payload for initiating an event simulation run.
    """
    scenario: SimulationScenario = Field(
        default=SimulationScenario.PAYMENT_FAILURE_SPIKE,
        description="Scenario pattern to simulate"
    )
    events_per_second: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Target event generation rate in events/second (1-50)"
    )
    duration_seconds: int = Field(
        default=60,
        ge=5,
        le=300,
        description="Total simulation duration in seconds (5-300)"
    )
    service: Optional[str] = Field(
        default="payment-service",
        max_length=100,
        description="Target service identifier to simulate"
    )
    region: Optional[str] = Field(
        default="Pune",
        max_length=100,
        description="Target geographic region / datacenter"
    )


class SimulatorStatusResponse(BaseModel):
    """
    Live status response of the event simulator.
    """
    running: bool = Field(description="Whether a simulation is actively running")
    scenario: Optional[str] = Field(None, description="Active or last simulated scenario")
    events_generated: int = Field(0, description="Total events generated in this run")
    elapsed_seconds: int = Field(0, description="Seconds elapsed since simulation start")
    duration_seconds: int = Field(0, description="Target total duration in seconds")
    events_per_second: int = Field(0, description="Target event generation rate")
    service: Optional[str] = Field(None, description="Target service")
    region: Optional[str] = Field(None, description="Target region")
    message: Optional[str] = Field(None, description="Descriptive status message")
