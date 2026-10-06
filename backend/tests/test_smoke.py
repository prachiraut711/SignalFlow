"""
Automated End-to-End Smoke Test for SignalFlow Pipeline (Phase 9)

Verifies the complete lifecycle:
POST /api/events -> Redis Stream -> Worker Processing -> DuckDB Analytics
-> Anomaly Detection -> Signal Correlation -> AI Explanation Mock -> Resolution.
"""

from datetime import datetime, timezone, timedelta
import json
from unittest.mock import AsyncMock, patch
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.duckdb import DuckDBService, get_duckdb_service
from app.db.postgres import get_db
from app.models import Base, SignalRecord, AnomalyRecord
from app.services.redis_service import get_redis_service, RedisService
from app.services.event_service import EventService
from app.services.analytics_service import AnalyticsService
from app.services.anomaly_service import AnomalyService
from app.services.signal_service import SignalService
from app.workers.event_worker import EventWorker

client = TestClient(app)


@pytest.fixture
def smoke_env():
    """Isolated environment with in-memory DuckDB and SQLite."""
    # 1. In-memory SQLite for relational store
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()

    # 2. In-memory DuckDB for analytical store
    duckdb_svc = DuckDBService(db_path=":memory:")

    # 3. RedisService with FakeRedis fallback
    redis_svc = RedisService(redis_url="redis://localhost:6379/0")

    yield {
        "session": session,
        "duckdb": duckdb_svc,
        "redis": redis_svc,
    }

    session.close()


@pytest.mark.asyncio
async def test_end_to_end_pipeline_smoke(smoke_env):
    """
    Executes the full SignalFlow pipeline end-to-end:
    1. Ingestion: POST /api/events -> Stream
    2. Processing: Worker batch consumption -> DuckDB
    3. Analytics: GET /api/analytics/overview & /services
    4. Anomaly Detection: AnomalyService -> DB Persistence
    5. Incident Correlation: SignalService -> Incident creation
    6. Signal API: GET /api/signals and POST /resolve
    7. AI Explanation: Mocked OpenRouter response verification
    """
    session: Session = smoke_env["session"]
    duckdb_svc: DuckDBService = smoke_env["duckdb"]
    redis_svc: RedisService = smoke_env["redis"]

    # Configure FastAPI dependency overrides
    app.dependency_overrides[get_db] = lambda: session
    app.dependency_overrides[get_duckdb_service] = lambda: duckdb_svc
    app.dependency_overrides[get_redis_service] = lambda: redis_svc

    try:
        # ---------------------------------------------------------------------
        # Step 1: Ingest events via API (POST /api/events)
        # ---------------------------------------------------------------------
        stream_test_name = "signalflow:test:smoke"
        event_svc = EventService(redis_service=redis_svc)

        # Ingest baseline normal events
        now = datetime.now(timezone.utc)
        baseline_events = []
        for i in range(5):
            t = (now - timedelta(minutes=5 - i)).isoformat()
            res = client.post("/api/events", json={
                "timestamp": t,
                "service": "payment-service",
                "event_type": "payment_success",
                "region": "Pune",
                "status_code": 200,
                "latency_ms": 320.0,
                "value": 1500.0,
                "user_id": f"smoke_user_{i}",
                "metadata": {"test": "smoke_baseline"}
            })
            assert res.status_code == 201
            assert res.json()["success"] is True

        # Ingest anomaly events (spike in errors & latency)
        anomaly_payloads = [
            {
                "timestamp": now.isoformat(),
                "service": "payment-service",
                "event_type": "payment_failed",
                "region": "Pune",
                "status_code": 500,
                "latency_ms": 2800.0,
                "value": 1500.0,
                "user_id": f"smoke_fail_{j}",
                "metadata": {"test": "smoke_anomaly"}
            }
            for j in range(3)
        ]
        for p in anomaly_payloads:
            res = client.post("/api/events", json=p)
            assert res.status_code == 201

        # ---------------------------------------------------------------------
        # Step 2: Worker Processing (Redis Stream -> DuckDB)
        # ---------------------------------------------------------------------
        worker = EventWorker(
            redis_service=redis_svc,
            duckdb_service=duckdb_svc,
            stream_name="signalflow:events",
            group_name="smoke-workers",
            consumer_name="smoke-consumer-1",
            batch_size=50,
            block_ms=100,
        )
        await worker.initialize_consumer_group()
        processed_count = await worker.process_batch()
        assert processed_count == 8  # 5 baseline + 3 anomaly events

        # Verify DuckDB has exactly 8 events
        count_res = duckdb_svc.query("SELECT COUNT(*) FROM events")
        assert count_res[0][0] == 8

        # ---------------------------------------------------------------------
        # Step 3: Analytics API Verification
        # ---------------------------------------------------------------------
        res_overview = client.get("/api/analytics/overview")
        assert res_overview.status_code == 200
        overview_data = res_overview.json()
        assert overview_data["total_events"] == 8
        assert overview_data["total_errors"] == 3
        assert round(overview_data["error_rate"], 1) == 37.5

        res_services = client.get("/api/analytics/services")
        assert res_services.status_code == 200
        svc_data = res_services.json()
        assert len(svc_data) >= 1
        payment_metrics = next(s for s in svc_data if s["service"] == "payment-service")
        assert payment_metrics["event_count"] == 8
        assert payment_metrics["error_count"] == 3

        # ---------------------------------------------------------------------
        # Step 4: Anomaly Detection Engine
        # ---------------------------------------------------------------------
        anomaly_svc = AnomalyService(duckdb_service=duckdb_svc, db_session=session)
        det_result = anomaly_svc.run_anomaly_detection(session=session)
        assert det_result["services_scanned"] >= 1
        assert det_result["anomalies_detected"] >= 1

        # Check anomalies in database
        anomalies = anomaly_svc.get_anomalies(service="payment-service", session=session)
        assert len(anomalies) >= 1
        assert any(a.metric in ("error_rate", "average_latency_ms") for a in anomalies)

        # ---------------------------------------------------------------------
        # Step 5: Incident Correlation Engine
        # ---------------------------------------------------------------------
        signal_svc = SignalService()
        corr_result = signal_svc.create_or_update_signals(session=session)
        assert corr_result["signals_created"] >= 1
        assert corr_result["anomalies_correlated"] >= 1

        # ---------------------------------------------------------------------
        # Step 6: Signal API Endpoints
        # ---------------------------------------------------------------------
        res_signals = client.get("/api/signals?status=OPEN")
        assert res_signals.status_code == 200
        signals_list = res_signals.json()
        assert len(signals_list) >= 1
        target_signal = signals_list[0]
        sig_id = target_signal["id"]
        assert target_signal["service"] == "payment-service"
        assert target_signal["status"] == "OPEN"

        # Signal detail endpoint
        res_detail = client.get(f"/api/signals/{sig_id}")
        assert res_detail.status_code == 200
        assert res_detail.json()["id"] == sig_id

        # ---------------------------------------------------------------------
        # Step 7: AI Explanation with Mocked OpenRouter
        # ---------------------------------------------------------------------
        mock_ai_response = {
            "summary": "Elevated failure rate and high response latency detected in payment gateway.",
            "likely_causes": [
                "Payment gateway upstream timeout",
                "Network packet loss between payment-service and acquirer bank"
            ],
            "recommended_actions": [
                "Inspect payment gateway connection pool",
                "Verify acquiring bank status and switch to fallback gateway"
            ]
        }

        import httpx
        from app.services.ai_explanation_service import AIExplanationService, get_ai_explanation_service

        mock_resp = httpx.Response(
            status_code=200,
            json={"choices": [{"message": {"role": "assistant", "content": json.dumps(mock_ai_response)}}]},
            request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
        )
        mock_http = AsyncMock(spec=httpx.AsyncClient)
        mock_http.post = AsyncMock(return_value=mock_resp)

        app.dependency_overrides[get_ai_explanation_service] = lambda: AIExplanationService(
            api_key="sk-or-smoke-mock-key",
            http_client=mock_http,
        )

        res_explain = client.post(f"/api/signals/{sig_id}/explain")
        assert res_explain.status_code == 200
        explain_data = res_explain.json()
        assert "summary" in explain_data
        assert "likely_causes" in explain_data
        assert len(explain_data["likely_causes"]) >= 1

        # ---------------------------------------------------------------------
        # Step 8: Signal Resolution Lifecycle
        # ---------------------------------------------------------------------
        res_resolve = client.post(f"/api/signals/{sig_id}/resolve")
        assert res_resolve.status_code == 200
        assert res_resolve.json()["status"] == "RESOLVED"

        # Verify no open signals remain
        res_open_after = client.get("/api/signals?status=OPEN")
        assert len(res_open_after.json()) == 0

    finally:
        app.dependency_overrides.clear()
