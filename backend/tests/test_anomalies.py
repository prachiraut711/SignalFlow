"""
Automated Test Suite for Phase 4:
Statistical Anomaly Detection, Isolation Forest, Anomaly Service, and Anomaly APIs
"""

from datetime import datetime, timezone
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

from app.main import app
from app.db.duckdb import DuckDBService, get_duckdb_service
from app.db.postgres import get_db
from app.models.anomaly import Base, AnomalyRecord
from app.ml.statistical_detector import (
    calculate_z_score,
    detect_percentage_change,
    detect_statistical_anomaly,
    determine_severity,
)
from app.ml.anomaly_detector import IsolationForestDetector
from app.services.anomaly_service import AnomalyService

client = TestClient(app)


# ==============================================================================
# 1. Statistical Detector Unit Tests
# ==============================================================================

def test_statistical_normal_value():
    """Verify normal metric variance is NOT flagged as an anomaly."""
    baseline = [3.0, 3.1, 2.9, 3.2, 3.0]
    result = detect_statistical_anomaly("error_rate", current_value=3.1, baseline_values=baseline)
    assert result is None


def test_statistical_moderate_deviation():
    """Verify moderate deviation is flagged with appropriate severity."""
    baseline = [3.0, 5.0, 4.0, 6.0, 3.5]
    result = detect_statistical_anomaly("error_rate", current_value=8.0, baseline_values=baseline)
    assert result is not None
    assert result["is_anomaly"] is True
    assert result["severity"] in ("WARNING", "HIGH")
    assert result["percentage_change"] > 70.0


def test_statistical_extreme_deviation():
    """Verify extreme spike is flagged as CRITICAL severity."""
    baseline = [3.0, 3.1, 2.9, 3.2, 3.0]
    result = detect_statistical_anomaly("error_rate", current_value=22.0, baseline_values=baseline)
    assert result is not None
    assert result["is_anomaly"] is True
    assert result["severity"] == "CRITICAL"
    assert result["z_score"] > 4.0
    assert "Critical error surge" in result["reason"]


def test_statistical_latency_spike():
    """Verify latency degradation beyond threshold is detected as anomaly."""
    baseline = [320.0, 310.0, 330.0, 305.0, 315.0]
    result = detect_statistical_anomaly("average_latency_ms", current_value=1950.0, baseline_values=baseline)
    assert result is not None
    assert result["is_anomaly"] is True
    assert result["anomaly_type"] == "latency_spike"
    assert result["severity"] in ("HIGH", "CRITICAL")
    assert result["percentage_change"] > 400.0


def test_statistical_traffic_volume_anomaly():
    """Verify sudden traffic volume surge triggers volume deviation anomaly."""
    baseline = [100.0, 105.0, 98.0, 102.0, 100.0]
    result = detect_statistical_anomaly("event_count", current_value=350.0, baseline_values=baseline)
    assert result is not None
    assert result["is_anomaly"] is True
    assert result["anomaly_type"] == "traffic_surge"
    assert result["percentage_change"] >= 200.0


def test_statistical_zero_std_handling():
    """Verify zero variance in baseline does not cause division by zero."""
    baseline = [4.0, 4.0, 4.0, 4.0]
    # Exactly equal to mean with zero std -> not an anomaly
    normal_res = detect_statistical_anomaly("error_rate", current_value=4.0, baseline_values=baseline)
    assert normal_res is None

    # Significant jump from zero variance -> handled cleanly via % change
    spike_res = detect_statistical_anomaly("error_rate", current_value=18.0, baseline_values=baseline)
    assert spike_res is not None
    assert spike_res["is_anomaly"] is True


def test_severity_classification_all_tiers():
    """Verify INFO, WARNING, HIGH, and CRITICAL classifications."""
    sev_crit, _ = determine_severity("error_rate", current=20.0, baseline=3.0, z_score=4.5, pct_change=566.0)
    assert sev_crit == "CRITICAL"

    sev_high, _ = determine_severity("error_rate", current=10.0, baseline=3.0, z_score=2.8, pct_change=233.0)
    assert sev_high == "HIGH"

    sev_warn, _ = determine_severity("error_rate", current=5.5, baseline=3.0, z_score=2.1, pct_change=83.0)
    assert sev_warn == "WARNING"

    sev_info, _ = determine_severity("error_rate", current=3.5, baseline=3.0, z_score=1.2, pct_change=16.0)
    assert sev_info == "INFO"


# ==============================================================================
# 2. Isolation Forest Detector Unit Tests
# ==============================================================================

def test_isolation_forest_synthetic_data():
    """Verify Isolation Forest accurately identifies multivariate outlier."""
    detector = IsolationForestDetector(contamination=0.1, random_state=42)

    # 15 typical normal baseline windows: ~100 events, 3% errors, 400ms latency
    normal_windows = [
        {"event_count": 100 + i, "error_rate": 3.0 + (i % 2) * 0.2, "average_latency_ms": 400.0 + i * 2}
        for i in range(15)
    ]

    # Test normal window
    normal_test = {"event_count": 102, "error_rate": 3.1, "average_latency_ms": 405.0}
    norm_result = detector.detect(normal_windows, normal_test)
    assert norm_result["fitted"] is True
    assert norm_result["is_anomaly"] is False
    assert norm_result["isolation_score"] >= 0.0

    # Test extreme outlier window: 25% errors, 2400ms latency
    outlier_test = {"event_count": 110, "error_rate": 25.0, "average_latency_ms": 2400.0}
    outlier_result = detector.detect(normal_windows, outlier_test)
    assert outlier_result["fitted"] is True
    assert outlier_result["is_anomaly"] is True
    assert outlier_result["isolation_score"] < 0.0


# ==============================================================================
# 3. Anomaly Persistence & Deduplication Tests
# ==============================================================================

from sqlalchemy.pool import StaticPool

@pytest.fixture
def sqlite_session() -> Session:
    """Fixture providing an isolated in-memory SQLite database for testing PostgreSQL models."""
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


def test_anomaly_persistence_and_deduplication(sqlite_session: Session):
    """
    Verify that anomalies are detected and persisted, and that subsequent detection
    runs on the same time window do NOT create duplicate entries.
    """
    # Create in-memory DuckDB containing 5 baseline windows + 1 abnormal window
    duckdb_svc = DuckDBService(db_path=":memory:")

    events_data = []
    # 5 normal windows (minutes 00 to 04)
    for m in range(5):
        events_data.append({
            "event_id": f"evt_norm_{m}",
            "timestamp": f"2026-10-05T14:0{m}:00Z",
            "service": "payment-service",
            "event_type": "payment_success",
            "region": "Pune",
            "status_code": 200,
            "latency_ms": 400.0,
            "value": 1000.0,
            "user_id": "u1",
            "ingested_at": f"2026-10-05T14:0{m}:01Z",
        })

    # 1 abnormal window (minute 05): high error + high latency
    events_data.append({
        "event_id": "evt_abnorm_1",
        "timestamp": "2026-10-05T14:05:00Z",
        "service": "payment-service",
        "event_type": "payment_failed",
        "region": "Pune",
        "status_code": 500,
        "latency_ms": 2400.0,
        "value": 1000.0,
        "user_id": "u2",
        "ingested_at": "2026-10-05T14:05:01Z",
    })

    duckdb_svc.insert_events_batch(events_data)

    anomaly_svc = AnomalyService(duckdb_service=duckdb_svc, db_session=sqlite_session)

    # First detection pass
    run1 = anomaly_svc.run_anomaly_detection(session=sqlite_session)
    assert run1["anomalies_detected"] >= 1

    stored = anomaly_svc.get_anomalies(service="payment-service", session=sqlite_session)
    count_first_run = len(stored)
    assert count_first_run >= 1

    # Verify attributes of stored record
    first_anomaly = stored[0]
    assert first_anomaly.service == "payment-service"
    assert first_anomaly.percentage_change >= 100.0 or first_anomaly.z_score is not None

    # Second detection pass: MUST NOT create duplicate records
    run2 = anomaly_svc.run_anomaly_detection(session=sqlite_session)
    assert run2["anomalies_detected"] == 0

    stored_after = anomaly_svc.get_anomalies(service="payment-service", session=sqlite_session)
    assert len(stored_after) == count_first_run


# ==============================================================================
# 4. Anomaly API Tests
# ==============================================================================

def test_api_anomalies_endpoints(sqlite_session: Session):
    """Test GET /api/anomalies endpoint with filtering."""
    # Seed an anomaly in test SQLite session
    rec = AnomalyRecord(
        detected_at=datetime.now(timezone.utc),
        time_window=datetime.now(timezone.utc),
        service="order-service",
        region="Pune",
        metric="error_rate",
        anomaly_type="error_rate_spike",
        current_value=18.5,
        baseline_value=2.0,
        percentage_change=825.0,
        z_score=4.12,
        isolation_score=-0.45,
        severity="CRITICAL",
        reason="Error rate is significantly above baseline",
    )
    sqlite_session.add(rec)
    sqlite_session.commit()

    app.dependency_overrides[get_db] = lambda: sqlite_session
    try:
        response = client.get("/api/anomalies")
        assert response.status_code == 200
        data = response.json()
        assert len(data) >= 1
        assert data[0]["service"] == "order-service"
        assert data[0]["severity"] == "CRITICAL"
        assert data[0]["metric"] == "error_rate"

        # Test service filter
        res_filter = client.get("/api/anomalies?service=non-existent-service")
        assert res_filter.status_code == 200
        assert len(res_filter.json()) == 0
    finally:
        app.dependency_overrides.clear()
