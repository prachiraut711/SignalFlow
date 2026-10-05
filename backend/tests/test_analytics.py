"""
Automated Unit and Functional Tests for Phase 3:
Event Worker, DuckDB Analytics Storage, and Analytics Query APIs
"""

from datetime import datetime, timezone
import json
from unittest.mock import AsyncMock, MagicMock
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.db.duckdb import DuckDBService, get_duckdb_service
from app.services.analytics_service import AnalyticsService
from app.workers.event_worker import EventWorker

client = TestClient(app)

SAMPLE_EVENTS = [
    {
        "event_id": "evt_p1",
        "timestamp": "2026-10-05T14:30:00Z",
        "service": "payment-service",
        "event_type": "payment_success",
        "region": "Pune",
        "status_code": 200,
        "latency_ms": 400.0,
        "value": 1499.0,
        "user_id": "u1",
        "ingested_at": "2026-10-05T14:30:01Z",
    },
    {
        "event_id": "evt_p2",
        "timestamp": "2026-10-05T14:30:10Z",
        "service": "payment-service",
        "event_type": "payment_failed",
        "region": "Pune",
        "status_code": 500,
        "latency_ms": 2200.0,
        "value": 1499.0,
        "user_id": "u2",
        "ingested_at": "2026-10-05T14:30:11Z",
    },
    {
        "event_id": "evt_p3",
        "timestamp": "2026-10-05T14:30:20Z",
        "service": "payment-service",
        "event_type": "payment_failed",
        "region": "Pune",
        "status_code": 500,
        "latency_ms": 2500.0,
        "value": 1499.0,
        "user_id": "u3",
        "ingested_at": "2026-10-05T14:30:21Z",
    },
    {
        "event_id": "evt_o1",
        "timestamp": "2026-10-05T14:30:30Z",
        "service": "order-service",
        "event_type": "order_created",
        "region": "Pune",
        "status_code": 200,
        "latency_ms": 300.0,
        "value": 2999.0,
        "user_id": "u4",
        "ingested_at": "2026-10-05T14:30:31Z",
    },
    {
        "event_id": "evt_o2",
        "timestamp": "2026-10-05T14:30:40Z",
        "service": "order-service",
        "event_type": "api_error",
        "region": "Pune",
        "status_code": 500,
        "latency_ms": 900.0,
        "value": 0.0,
        "user_id": "u5",
        "ingested_at": "2026-10-05T14:30:41Z",
    },
]


@pytest.fixture
def in_memory_duckdb() -> DuckDBService:
    """Fixture providing an isolated in-memory DuckDB database with initialized schema."""
    service = DuckDBService(db_path=":memory:")
    service.insert_events_batch(SAMPLE_EVENTS)
    return service


# ==============================================================================
# 1. DuckDB Storage & Aggregation Calculation Tests
# ==============================================================================

def test_duckdb_insert_and_count(in_memory_duckdb: DuckDBService):
    """Verify DuckDB stores and queries inserted event records accurately."""
    rows = in_memory_duckdb.query("SELECT COUNT(*) FROM events")
    assert rows[0][0] == 5


def test_analytics_service_metrics(in_memory_duckdb: DuckDBService):
    """
    Verify analytics calculations match sample event data:
    5 events, 3 errors (60.0%), total latency 6300ms / 5 = 1260.0ms.
    """
    analytics = AnalyticsService(duckdb_service=in_memory_duckdb)

    assert analytics.get_event_count() == 5
    assert analytics.get_error_count() == 3
    assert analytics.get_error_rate() == 60.0
    assert analytics.get_average_latency() == 1260.0

    overview = analytics.get_overview()
    assert overview.total_events == 5
    assert overview.total_errors == 3
    assert overview.error_rate == 60.0
    assert overview.average_latency_ms == 1260.0


def test_analytics_service_grouped_by_service(in_memory_duckdb: DuckDBService):
    """
    Verify metrics broken down by individual microservice:
    payment-service: 3 events, 2 errors (66.67%), avg latency 1700.0ms
    order-service:   2 events, 1 error  (50.0%),  avg latency 600.0ms
    """
    analytics = AnalyticsService(duckdb_service=in_memory_duckdb)
    service_metrics = analytics.get_service_metrics()

    assert len(service_metrics) == 2
    metrics_map = {m.service: m for m in service_metrics}

    # payment-service checks
    ps = metrics_map["payment-service"]
    assert ps.event_count == 3
    assert ps.error_count == 2
    assert ps.error_rate == 66.67
    assert ps.average_latency_ms == 1700.0

    # order-service checks
    os = metrics_map["order-service"]
    assert os.event_count == 2
    assert os.error_count == 1
    assert os.error_rate == 50.0
    assert os.average_latency_ms == 600.0


# ==============================================================================
# 2. Analytics API Endpoint Tests
# ==============================================================================

def test_api_analytics_overview(in_memory_duckdb: DuckDBService):
    """Test GET /api/analytics/overview endpoint."""
    app.dependency_overrides[get_duckdb_service] = lambda: in_memory_duckdb
    try:
        response = client.get("/api/analytics/overview")
        assert response.status_code == 200
        data = response.json()
        assert data["total_events"] == 5
        assert data["total_errors"] == 3
        assert data["error_rate"] == 60.0
        assert data["average_latency_ms"] == 1260.0
    finally:
        app.dependency_overrides.clear()


def test_api_analytics_services(in_memory_duckdb: DuckDBService):
    """Test GET /api/analytics/services endpoint."""
    app.dependency_overrides[get_duckdb_service] = lambda: in_memory_duckdb
    try:
        response = client.get("/api/analytics/services")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)
        assert len(data) == 2

        services = [item["service"] for item in data]
        assert "payment-service" in services
        assert "order-service" in services
    finally:
        app.dependency_overrides.clear()


# ==============================================================================
# 3. EventWorker Unit Tests
# ==============================================================================

def test_worker_parse_valid_message():
    """Verify worker parses JSON payload string from Redis Stream fields."""
    worker = EventWorker(duckdb_service=DuckDBService(db_path=":memory:"))
    raw_fields = {
        "event_id": "evt_w1",
        "service": "cart-service",
        "event_type": "api_request",
        "payload": json.dumps({
            "event_id": "evt_w1",
            "timestamp": "2026-10-05T14:30:00Z",
            "service": "cart-service",
            "event_type": "api_request",
            "region": "Pune",
            "status_code": 200,
            "latency_ms": 120.0,
            "value": 0.0,
            "user_id": "u99",
            "ingested_at": "2026-10-05T14:30:01Z",
        })
    }

    parsed = worker.parse_message_payload("1000-0", raw_fields)
    assert parsed is not None
    assert parsed["event_id"] == "evt_w1"
    assert parsed["service"] == "cart-service"
    assert parsed["latency_ms"] == 120.0


def test_worker_parse_malformed_message():
    """Verify worker returns None on malformed payload without raising exceptions."""
    worker = EventWorker(duckdb_service=DuckDBService(db_path=":memory:"))
    malformed_fields = {
        "payload": "invalid-json-string{{"
    }
    parsed = worker.parse_message_payload("1000-1", malformed_fields)
    assert parsed is None


@pytest.mark.asyncio
async def test_worker_process_batch_with_mocks():
    """Verify worker reads batch, persists into DuckDB, and ACKs Redis messages."""
    mock_redis = AsyncMock()
    mock_redis.read_consumer_group.return_value = [
        (
            "signalflow:events",
            [
                (
                    "1001-0",
                    {
                        "event_id": "evt_mock_1",
                        "service": "test-service",
                        "event_type": "api_request",
                        "payload": json.dumps({
                            "event_id": "evt_mock_1",
                            "timestamp": "2026-10-05T14:30:00Z",
                            "service": "test-service",
                            "event_type": "api_request",
                            "region": "Pune",
                            "status_code": 200,
                            "latency_ms": 85.0,
                            "value": 0.0,
                            "user_id": "u1",
                            "ingested_at": "2026-10-05T14:30:01Z",
                        }),
                    },
                )
            ],
        )
    ]
    mock_redis.ack_messages.return_value = 1

    in_mem_db = DuckDBService(db_path=":memory:")
    worker = EventWorker(redis_service=mock_redis, duckdb_service=in_mem_db)

    count = await worker.process_batch()
    assert count == 1

    # Verify event landed in DuckDB
    rows = in_mem_db.query("SELECT event_id, service, latency_ms FROM events WHERE event_id = 'evt_mock_1'")
    assert len(rows) == 1
    assert rows[0][0] == "evt_mock_1"
    assert rows[0][1] == "test-service"
    assert rows[0][2] == 85.0

    # Verify ACK was dispatched
    assert mock_redis.ack_messages.called
    ack_args = mock_redis.ack_messages.call_args[0]
    assert "1001-0" in ack_args
