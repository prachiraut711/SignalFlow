"""
Health Endpoint Verification Tests
"""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_endpoint():
    """Verify that GET /health returns status 200 and expected payload."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "signalflow-backend"
    }


def test_root_endpoint():
    """Verify that GET / returns status 200 with operational message."""
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "operational"
    assert "SignalFlow" in data["message"]


def test_api_v1_health_endpoint():
    """Verify that GET /api/v1/health also returns status 200."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "signalflow-backend"
    }
