"""
Automated Test Suite for SignalFlow Event Pipeline and Redis Integration
"""

from unittest.mock import AsyncMock, patch
import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.event import EventCreate, EventType
from app.services.event_service import EventService
from app.services.redis_service import get_redis_service, RedisService

client = TestClient(app)


# Sample valid payload
VALID_EVENT_PAYLOAD = {
    "timestamp": "2026-10-05T14:30:00Z",
    "service": "payment-service",
    "event_type": "payment_failed",
    "region": "Pune",
    "status_code": 500,
    "latency_ms": 2300,
    "value": 1499.0,
    "user_id": "user_123",
    "metadata": {"error_code": "ERR_GATEWAY_TIMEOUT"}
}


# ==============================================================================
# 1. Pydantic Schema Validation Tests
# ==============================================================================

def test_valid_event_schema():
    """Verify that a valid event dictionary parses successfully."""
    event = EventCreate(**VALID_EVENT_PAYLOAD)
    assert event.service == "payment-service"
    assert event.event_type == EventType.PAYMENT_FAILED
    assert event.region == "Pune"
    assert event.status_code == 500
    assert event.latency_ms == 2300.0
    assert event.value == 1499.0
    assert event.user_id == "user_123"
    assert event.metadata["error_code"] == "ERR_GATEWAY_TIMEOUT"


def test_invalid_event_schema_empty_service_and_negative_latency():
    """Verify that empty service and negative latency trigger validation errors."""
    invalid_payload = {
        "timestamp": "2026-10-05T14:30:00Z",
        "service": "   ",
        "event_type": "payment_failed",
        "status_code": 500,
        "latency_ms": -20.0,
    }
    with pytest.raises(ValidationError) as exc_info:
        EventCreate(**invalid_payload)
    
    errors = str(exc_info.value)
    assert "latency_ms" in errors
    assert "service" in errors


def test_invalid_event_type():
    """Verify that unsupported event types are rejected."""
    invalid_payload = {
        **VALID_EVENT_PAYLOAD,
        "event_type": "unsupported_custom_action"
    }
    with pytest.raises(ValidationError):
        EventCreate(**invalid_payload)


def test_invalid_status_code_range():
    """Verify that non-HTTP status codes (<100 or >599) are rejected."""
    invalid_payload = {
        **VALID_EVENT_PAYLOAD,
        "status_code": 999
    }
    with pytest.raises(ValidationError):
        EventCreate(**invalid_payload)


# ==============================================================================
# 2. EventService Unit Tests (Mocked Redis)
# ==============================================================================

@pytest.mark.asyncio
async def test_event_service_ingest_mocked_redis():
    """Verify EventService generates ID, enriches payload, and calls Redis XADD."""
    mock_redis = AsyncMock(spec=RedisService)
    mock_redis.add_to_stream.return_value = "1728148200000-0"

    service = EventService(redis_service=mock_redis)
    event_model = EventCreate(**VALID_EVENT_PAYLOAD)

    response = await service.ingest_event(event_model)

    assert response.success is True
    assert response.message == "Event accepted"
    assert response.event_id.startswith("evt_")
    assert mock_redis.add_to_stream.called

    call_args = mock_redis.add_to_stream.call_args[1]
    stream_fields = call_args["fields"]
    assert stream_fields["event_id"] == response.event_id
    assert stream_fields["service"] == "payment-service"
    assert stream_fields["event_type"] == "payment_failed"
    assert "payload" in stream_fields


# ==============================================================================
# 3. API Endpoint Tests (POST /api/events)
# ==============================================================================

def test_api_post_event_success():
    """Test POST /api/events endpoint with mocked Redis dependency."""
    mock_redis = AsyncMock(spec=RedisService)
    mock_redis.add_to_stream.return_value = "1728148200000-0"

    app.dependency_overrides[get_redis_service] = lambda: mock_redis

    try:
        response = client.post("/api/events", json=VALID_EVENT_PAYLOAD)
        assert response.status_code == 201
        data = response.json()
        assert data["success"] is True
        assert data["message"] == "Event accepted"
        assert data["event_id"].startswith("evt_")
    finally:
        app.dependency_overrides.clear()


def test_api_post_event_validation_failure():
    """Test POST /api/events rejects invalid payload with HTTP 422."""
    bad_payload = {
        "timestamp": "2026-10-05T14:30:00Z",
        "service": "",
        "event_type": "payment_failed",
        "latency_ms": -20
    }
    response = client.post("/api/events", json=bad_payload)
    assert response.status_code == 422
    assert "detail" in response.json()


# ==============================================================================
# 4. Redis Health Check Tests
# ==============================================================================

def test_redis_health_healthy():
    """Verify GET /health/redis returns healthy when Redis responds."""
    mock_redis = AsyncMock(spec=RedisService)
    mock_redis.ping.return_value = True

    app.dependency_overrides[get_redis_service] = lambda: mock_redis
    try:
        response = client.get("/health/redis")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "redis"
    finally:
        app.dependency_overrides.clear()


def test_redis_health_unhealthy():
    """Verify GET /health/redis returns 503 and unhealthy status when Redis is down."""
    mock_redis = AsyncMock(spec=RedisService)
    mock_redis.ping.return_value = False

    app.dependency_overrides[get_redis_service] = lambda: mock_redis
    try:
        response = client.get("/health/redis")
        assert response.status_code == 503
        data = response.json()
        assert data["status"] == "unhealthy"
        assert data["service"] == "redis"
    finally:
        app.dependency_overrides.clear()
