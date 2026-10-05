"""
Pydantic Schemas for AI Incident Explanations
"""

from datetime import datetime
from typing import List
from pydantic import BaseModel, Field


class AIExplanationResponse(BaseModel):
    """Structured AI incident diagnostic explanation returned to clients."""
    signal_id: int
    summary: str = Field(..., description="High-level incident summary")
    likely_causes: List[str] = Field(..., description="Plausible hypotheses for the operational incident")
    recommended_actions: List[str] = Field(..., description="Actionable triage, verification, and remediation steps")
    model: str = Field(..., description="LLM model identifier utilized")
    generated_at: datetime = Field(..., description="Timestamp of generation")

    model_config = {"from_attributes": True}
