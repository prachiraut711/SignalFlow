"""
Pydantic Request & Response Schemas
"""

from pydantic import BaseModel


class HealthResponse(BaseModel):
    """Schema for service health status."""
    status: str
    service: str
