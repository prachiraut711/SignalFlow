"""
Automated Test Suite for Phase 6:
AI Incident Explanation Layer using OpenRouter
"""

from datetime import datetime, timezone, timedelta
import json
import pytest
from unittest.mock import AsyncMock, patch
import httpx
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db.postgres import get_db
from app.models import Base, AnomalyRecord, SignalRecord, SignalAnomaly
from app.schemas.ai_explanation import AIExplanationResponse
from app.services.ai_explanation_service import (
    AIExplanationService,
    OpenRouterConfigError,
    OpenRouterServiceError,
    build_incident_prompt,
    clean_json_response,
    get_ai_explanation_service,
)

client = TestClient(app)


@pytest.fixture
def sqlite_session() -> Session:
    """Fixture providing an isolated in-memory SQLite database."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    yield session
    session.close()


def seed_test_signal(session: Session) -> SignalRecord:
    """Helper to seed a test Signal with 2 correlated anomalies."""
    t0 = datetime(2026, 10, 5, 20, 34, 0, tzinfo=timezone.utc)
    sig = SignalRecord(
        signal_key="SIG-payment-service-Pune-20261005203400",
        title="Payment Service Degradation",
        description="Payment Service in Pune is experiencing elevated errors and latency.",
        severity="CRITICAL",
        service="payment-service",
        region="Pune",
        status="OPEN",
        first_detected_at=t0,
        last_detected_at=t0,
        created_at=t0,
        updated_at=t0,
    )
    session.add(sig)
    session.flush()

    a1 = AnomalyRecord(
        detected_at=t0,
        time_window=t0,
        service="payment-service",
        region="Pune",
        metric="error_rate",
        anomaly_type="error_rate_spike",
        current_value=20.0,
        baseline_value=2.0,
        percentage_change=900.0,
        z_score=7.79,
        isolation_score=-0.059,
        severity="CRITICAL",
        reason="Critical error surge: error rate is 20.0% (+900.0% over 2.0% baseline)",
    )
    a2 = AnomalyRecord(
        detected_at=t0,
        time_window=t0,
        service="payment-service",
        region="Pune",
        metric="average_latency_ms",
        anomaly_type="latency_spike",
        current_value=2520.0,
        baseline_value=398.4,
        percentage_change=532.53,
        z_score=4593.4,
        isolation_score=-0.059,
        severity="CRITICAL",
        reason="Severe latency degradation: 2520.0ms (+532.53% over 398.4ms baseline)",
    )
    session.add(a1)
    session.add(a2)
    session.flush()

    sa1 = SignalAnomaly(signal_id=sig.id, anomaly_id=a1.id)
    sa2 = SignalAnomaly(signal_id=sig.id, anomaly_id=a2.id)
    session.add(sa1)
    session.add(sa2)
    sig.signal_anomalies.extend([sa1, sa2])
    session.commit()
    session.refresh(sig)
    return sig


# ==============================================================================
# 1. Prompt Construction & JSON Cleaning Tests
# ==============================================================================

def test_ai_service_builds_correct_incident_context(sqlite_session: Session):
    """Test 1: Verify the LLM prompt incorporates all telemetry without hallucination."""
    signal = seed_test_signal(sqlite_session)
    prompt = build_incident_prompt(signal)

    assert "Payment Service Degradation" in prompt
    assert "payment-service" in prompt
    assert "Pune" in prompt
    assert "CRITICAL" in prompt
    assert "error_rate" in prompt
    assert "average_latency_ms" in prompt
    assert "+900.00%" in prompt
    assert "2520.0" in prompt
    assert "Critical error surge" in prompt


def test_clean_json_response_strips_markdown_fences():
    """Verify markdown fences (```json ... ```) are cleanly stripped."""
    raw = "```json\n{\"summary\": \"Test summary\"}\n```"
    assert clean_json_response(raw) == '{"summary": "Test summary"}'

    raw_plain = '{"summary": "Plain"}'
    assert clean_json_response(raw_plain) == '{"summary": "Plain"}'


# ==============================================================================
# 2. OpenRouter Client Unit Tests (Mocked)
# ==============================================================================

@pytest.mark.asyncio
async def test_successful_openrouter_response_parsing(sqlite_session: Session):
    """Test 2: Verify valid OpenRouter JSON response is parsed into AIExplanationResponse."""
    signal = seed_test_signal(sqlite_session)
    mock_llm_content = {
        "summary": "Payment service in Pune experienced critical degradation with elevated errors and latency.",
        "likely_causes": [
            "Upstream payment gateway timeout or throttling",
            "Database connection pool saturation in Pune region",
            "Recent service deployment regression"
        ],
        "recommended_actions": [
            "Check upstream payment partner health status",
            "Inspect database query latency and connection metrics",
            "Verify recent deployments or canary releases in Pune region"
        ]
    }

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "id": "gen-12345",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(mock_llm_content)
                    }
                }
            ]
        },
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    service = AIExplanationService(
        api_key="test-mock-key",
        model="openrouter/free",
        http_client=mock_client,
    )

    result = await service.generate_incident_explanation(signal)
    assert isinstance(result, AIExplanationResponse)
    assert result.signal_id == signal.id
    assert "Payment service in Pune experienced critical degradation" in result.summary
    assert len(result.likely_causes) == 3
    assert len(result.recommended_actions) == 3
    assert result.model == "openrouter/free"
    assert result.generated_at is not None


@pytest.mark.asyncio
async def test_missing_api_key_raises_config_error(sqlite_session: Session):
    """Test 3: Missing API key raises OpenRouterConfigError."""
    signal = seed_test_signal(sqlite_session)
    service = AIExplanationService(api_key="")

    with pytest.raises(OpenRouterConfigError) as exc_info:
        await service.generate_incident_explanation(signal)
    assert "OpenRouter API key is not configured" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openrouter_http_error_handled(sqlite_session: Session):
    """Test 4: OpenRouter 4xx/5xx status raises OpenRouterServiceError."""
    signal = seed_test_signal(sqlite_session)
    mock_resp = httpx.Response(
        status_code=502,
        content=b"Bad Gateway from upstream",
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    service = AIExplanationService(api_key="test-key", http_client=mock_client)

    with pytest.raises(OpenRouterServiceError) as exc_info:
        await service.generate_incident_explanation(signal)
    assert "AI explanation service is temporarily unavailable" in str(exc_info.value)


@pytest.mark.asyncio
async def test_openrouter_timeout_handled(sqlite_session: Session):
    """Test 5: OpenRouter request timeout raises OpenRouterServiceError."""
    signal = seed_test_signal(sqlite_session)
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(side_effect=httpx.TimeoutException("Connection timed out"))

    service = AIExplanationService(api_key="test-key", http_client=mock_client)

    with pytest.raises(OpenRouterServiceError) as exc_info:
        await service.generate_incident_explanation(signal)
    assert "timed out" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_malformed_ai_json_handled(sqlite_session: Session):
    """Test 6: Malformed/non-JSON response raises OpenRouterServiceError."""
    signal = seed_test_signal(sqlite_session)
    mock_resp = httpx.Response(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "I apologize, but I cannot format this as JSON."
                    }
                }
            ]
        },
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    service = AIExplanationService(api_key="test-key", http_client=mock_client)

    with pytest.raises(OpenRouterServiceError) as exc_info:
        await service.generate_incident_explanation(signal)
    assert "Failed to parse AI explanation response" in str(exc_info.value)


# ==============================================================================
# 3. API Endpoint Tests
# ==============================================================================

def test_api_signal_not_found_returns_404(sqlite_session: Session):
    """Test 7: Explaining a non-existent signal returns 404."""
    app.dependency_overrides[get_db] = lambda: sqlite_session
    try:
        response = client.post("/api/signals/99999/explain")
        assert response.status_code == 404
        assert "Signal with ID 99999 not found" in response.json()["detail"]
    finally:
        app.dependency_overrides.clear()


def test_api_missing_key_returns_503(sqlite_session: Session):
    """Test 3 (API): Missing API key returns 503 Service Unavailable."""
    signal = seed_test_signal(sqlite_session)
    app.dependency_overrides[get_db] = lambda: sqlite_session
    app.dependency_overrides[get_ai_explanation_service] = lambda: AIExplanationService(api_key="")
    try:
        response = client.post(f"/api/signals/{signal.id}/explain")
        assert response.status_code == 503
        assert response.json()["detail"] == "OpenRouter API key is not configured."
    finally:
        app.dependency_overrides.clear()


def test_api_successful_signal_explain_endpoint(sqlite_session: Session):
    """Test 8: Successful POST /api/signals/{id}/explain endpoint."""
    signal = seed_test_signal(sqlite_session)
    mock_payload = {
        "summary": "Payment service in Pune experienced elevated error rate and severe latency degradation.",
        "likely_causes": [
            "Third-party payment gateway connectivity disruption",
            "High database contention during peak transaction volume",
            "Configuration change impacting Pune regional nodes"
        ],
        "recommended_actions": [
            "Verify external payment gateway health status",
            "Check database query execution times and lock waits",
            "Review deployment logs for the payment-service in Pune"
        ]
    }

    mock_resp = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"role": "assistant", "content": json.dumps(mock_payload)}}]},
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )

    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    app.dependency_overrides[get_db] = lambda: sqlite_session
    app.dependency_overrides[get_ai_explanation_service] = lambda: AIExplanationService(
        api_key="mock-key-123",
        http_client=mock_client
    )

    try:
        response = client.post(f"/api/signals/{signal.id}/explain")
        assert response.status_code == 200
        data = response.json()
        assert data["signal_id"] == signal.id
        assert "Payment service in Pune experienced" in data["summary"]
        assert len(data["likely_causes"]) == 3
        assert len(data["recommended_actions"]) == 3
        assert data["model"] == "openrouter/free"
        assert "generated_at" in data
    finally:
        app.dependency_overrides.clear()


def test_api_does_not_expose_credentials(sqlite_session: Session):
    """Test 9: Secret API key is never leaked in API response body or headers."""
    signal = seed_test_signal(sqlite_session)
    secret_key = "super-secret-openrouter-key-999"

    mock_payload = {
        "summary": "Sample summary.",
        "likely_causes": ["Cause A"],
        "recommended_actions": ["Action A"]
    }
    mock_resp = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"role": "assistant", "content": json.dumps(mock_payload)}}]},
        request=httpx.Request("POST", "https://openrouter.ai/api/v1/chat/completions")
    )
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    mock_client.post = AsyncMock(return_value=mock_resp)

    app.dependency_overrides[get_db] = lambda: sqlite_session
    app.dependency_overrides[get_ai_explanation_service] = lambda: AIExplanationService(
        api_key=secret_key,
        http_client=mock_client
    )

    try:
        response = client.post(f"/api/signals/{signal.id}/explain")
        assert response.status_code == 200
        assert secret_key not in response.text
        for header_val in response.headers.values():
            assert secret_key not in header_val
    finally:
        app.dependency_overrides.clear()
