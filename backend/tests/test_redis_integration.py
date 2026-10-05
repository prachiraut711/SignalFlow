"""
Live Redis Integration Tests for SignalFlow Event Ingestion Pipeline

These tests interact with a live Redis instance (localhost:6379).
If Redis is not available, tests are skipped automatically.
"""

import json
import pytest
import httpx
from app.main import app
from app.services.redis_service import get_redis_service
from app.config import get_settings

settings = get_settings()


@pytest.mark.asyncio
async def test_live_redis_ping():
    """Verify live Redis ping check."""
    redis_service = get_redis_service()
    is_alive = await redis_service.ping()
    if not is_alive:
        pytest.skip("Live Redis server is not reachable on localhost:6379")
    assert is_alive is True


@pytest.mark.asyncio
async def test_live_event_ingestion_to_redis_stream():
    """Test full pipeline: POST /api/events -> Redis Stream XADD -> Read verification."""
    redis_service = get_redis_service()
    if not await redis_service.ping():
        pytest.skip("Live Redis server is not reachable on localhost:6379")

    payload = {
        "timestamp": "2026-10-05T14:30:00Z",
        "service": "order-service",
        "event_type": "order_created",
        "region": "Pune",
        "status_code": 201,
        "latency_ms": 145.5,
        "value": 2999.0,
        "user_id": "user_integration_test",
        "metadata": {"source": "pytest_integration"}
    }

    # 1. Send event to API using AsyncClient to share the same asyncio event loop
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        response = await ac.post("/api/events", json=payload)
    
    assert response.status_code == 201
    res_data = response.json()
    assert res_data["success"] is True
    assert res_data["message"] == "Event accepted"
    event_id = res_data["event_id"]
    assert event_id.startswith("evt_")

    # 2. Inspect Redis Stream to verify persistence
    entries = await redis_service.read_stream_latest(
        stream_name=settings.REDIS_STREAM_NAME,
        count=5
    )
    assert len(entries) > 0

    # Locate our event in the latest entries
    found = False
    for msg_id, fields in entries:
        if fields.get("event_id") == event_id:
            found = True
            assert fields["service"] == "order-service"
            assert fields["event_type"] == "order_created"
            stored_payload = json.loads(fields["payload"])
            assert stored_payload["event_id"] == event_id
            assert stored_payload["value"] == 2999.0
            assert stored_payload["user_id"] == "user_integration_test"
            break

    assert found is True, f"Event {event_id} was not found in Redis Stream '{settings.REDIS_STREAM_NAME}'"
