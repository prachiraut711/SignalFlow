"""
Pydantic Request & Response Schemas
"""

from typing import Optional
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    """Schema for service health status."""
    status: str
    service: str
    detail: Optional[str] = Field(default=None)
