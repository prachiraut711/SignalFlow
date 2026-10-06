"""
Automated Test Suite for Phase 5:
Signal Correlation, Incident Lifecycle, Title/Severity Generation, and Signal APIs
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, List
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from app.main import app
from app.db.postgres import get_db
from app.models import Base, AnomalyRecord, SignalRecord, SignalAnomaly
from app.services.signal_service import (
    SignalService,
    generate_signal_title,
    generate_signal_description,
    get_highest_severity,
    is_within_correlation_window,
    ensure_utc,
)

client = TestClient(app)


@pytest.fixture
def sqlite_session() -> Session:
    """Fixture providing an isolated in-memory SQLite database for signal testing."""
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


def create_sample_anomaly(
    session: Session,
    service: str = "payment-service",
    region: str = "Pune",
    metric: str = "error_rate",
    anomaly_type: str = "error_rate_spike",
    severity: str = "CRITICAL",
    time_window: Optional[datetime] = None,
    current_value: float = 20.0,
    baseline_value: float = 2.0,
    pct_change: float = 900.0,
) -> AnomalyRecord:
    """Helper to persist a test anomaly record."""
    if time_window is None:
        time_window = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    rec = AnomalyRecord(
        detected_at=time_window + timedelta(seconds=15),
        time_window=time_window,
        service=service,
        region=region,
        metric=metric,
        anomaly_type=anomaly_type,
        current_value=current_value,
        baseline_value=baseline_value,
        percentage_change=pct_change,
        z_score=5.0,
        isolation_score=-0.2,
        severity=severity,
        reason=f"{metric} deviation observed",
    )
    session.add(rec)
    session.commit()
    session.refresh(rec)
    return rec


# ==============================================================================
# 1. Deterministic Title, Description & Severity Generation Tests
# ==============================================================================

def test_signal_title_generation_all_variants(sqlite_session: Session):
    """Verify deterministic title generation across metric combinations."""
    base_time = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    
    # 1. Error only
    a_err = create_sample_anomaly(sqlite_session, metric="error_rate", time_window=base_time)
    assert generate_signal_title([a_err]) == "Payment Service Error Spike"

    # 2. Latency only
    a_lat = create_sample_anomaly(sqlite_session, metric="average_latency_ms", time_window=base_time)
    assert generate_signal_title([a_lat]) == "Payment Service Latency Degradation"

    # 3. Error + Latency
    assert generate_signal_title([a_err, a_lat]) == "Payment Service Degradation"

    # 4. Traffic / event count
    a_cnt = create_sample_anomaly(sqlite_session, metric="event_count", time_window=base_time)
    assert generate_signal_title([a_cnt]) == "Payment Service Traffic Anomaly"


def test_severity_priority_highest_selection():
    """Verify severity ordering selects the highest priority level."""
    assert get_highest_severity(["INFO", "WARNING"]) == "WARNING"
    assert get_highest_severity(["WARNING", "HIGH"]) == "HIGH"
    assert get_highest_severity(["HIGH", "CRITICAL"]) == "CRITICAL"
    assert get_highest_severity(["CRITICAL", "INFO", "WARNING"]) == "CRITICAL"
    assert get_highest_severity(["INFO"]) == "INFO"
    assert get_highest_severity([]) == "INFO"


# ==============================================================================
# 2. Correlation Window Logic Tests
# ==============================================================================

def test_correlation_window_proximity():
    """Verify time window correlation within 10 minutes vs outside."""
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    t_inside = datetime(2026, 10, 5, 14, 8, 0, tzinfo=timezone.utc)   # 8 min diff -> inside
    t_outside = datetime(2026, 10, 5, 14, 25, 0, tzinfo=timezone.utc)  # 25 min diff -> outside

    assert is_within_correlation_window(t_inside, t0, t0, max_delta_seconds=600) is True
    assert is_within_correlation_window(t_outside, t0, t0, max_delta_seconds=600) is False


# ==============================================================================
# 3. Signal Service Correlation Tests
# ==============================================================================

def test_signal_creation_single_anomaly(sqlite_session: Session):
    """Test 1: Signal creation from a single anomaly."""
    service = SignalService()
    a1 = create_sample_anomaly(sqlite_session, service="payment-service", severity="HIGH")

    result = service.create_or_update_signals(session=sqlite_session)
    assert result["signals_created"] == 1
    assert result["signals_updated"] == 0
    assert result["anomalies_correlated"] == 1

    signals = service.get_signals(session=sqlite_session)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.service == "payment-service"
    assert sig.status == "OPEN"
    assert sig.severity == "HIGH"
    assert sig.related_anomalies_count == 1
    assert len(sig.anomalies) == 1
    assert sig.anomalies[0].id == a1.id


def test_two_anomalies_same_service_region_become_one_signal(sqlite_session: Session):
    """Test 2: Two anomalies from same service/region within window correlate to 1 signal."""
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 5, 14, 4, 0, tzinfo=timezone.utc)

    a1 = create_sample_anomaly(sqlite_session, metric="error_rate", severity="CRITICAL", time_window=t0)
    a2 = create_sample_anomaly(sqlite_session, metric="average_latency_ms", severity="CRITICAL", time_window=t1)

    result = service.create_or_update_signals(session=sqlite_session)
    assert result["signals_created"] == 1
    assert result["signals_updated"] == 0
    assert result["anomalies_correlated"] == 2

    signals = service.get_signals(session=sqlite_session)
    assert len(signals) == 1
    sig = signals[0]
    assert sig.title == "Payment Service Degradation"
    assert sig.severity == "CRITICAL"
    assert sig.related_anomalies_count == 2
    assert ensure_utc(sig.first_detected_at) == t0
    assert ensure_utc(sig.last_detected_at) == t1


def test_different_services_create_separate_signals(sqlite_session: Session):
    """Test 3: Different services produce distinct signals even in the same region and time."""
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)

    create_sample_anomaly(sqlite_session, service="payment-service", region="Pune", time_window=t0)
    create_sample_anomaly(sqlite_session, service="order-service", region="Pune", time_window=t0)

    result = service.create_or_update_signals(session=sqlite_session)
    assert result["signals_created"] == 2
    assert result["anomalies_correlated"] == 2

    signals = service.get_signals(session=sqlite_session)
    assert len(signals) == 2
    services_found = {s.service for s in signals}
    assert services_found == {"payment-service", "order-service"}


def test_different_regions_create_separate_signals(sqlite_session: Session):
    """Test 4: Same service in different regions produce separate signals."""
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)

    create_sample_anomaly(sqlite_session, service="payment-service", region="Pune", time_window=t0)
    create_sample_anomaly(sqlite_session, service="payment-service", region="Bengaluru", time_window=t0)

    result = service.create_or_update_signals(session=sqlite_session)
    assert result["signals_created"] == 2

    signals = service.get_signals(session=sqlite_session)
    assert len(signals) == 2
    regions_found = {s.region for s in signals}
    assert regions_found == {"Pune", "Bengaluru"}


def test_anomalies_outside_correlation_window_do_not_correlate(sqlite_session: Session):
    """Test 5 & 6: Anomalies separated by >10 minutes create separate signals."""
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    t_later = datetime(2026, 10, 5, 14, 25, 0, tzinfo=timezone.utc)  # 25 mins later

    create_sample_anomaly(sqlite_session, service="payment-service", time_window=t0)
    create_sample_anomaly(sqlite_session, service="payment-service", time_window=t_later)

    result = service.create_or_update_signals(session=sqlite_session)
    assert result["signals_created"] == 2

    signals = service.get_signals(session=sqlite_session)
    assert len(signals) == 2


def test_severity_chooses_highest_from_anomalies(sqlite_session: Session):
    """Test 7: Signal severity upgrades to the highest severity among attached anomalies."""
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 5, 14, 3, 0, tzinfo=timezone.utc)

    # Anomaly 1 is WARNING, Anomaly 2 is HIGH
    create_sample_anomaly(sqlite_session, severity="WARNING", time_window=t0)
    create_sample_anomaly(sqlite_session, severity="HIGH", time_window=t1)

    result = service.create_or_update_signals(session=sqlite_session)
    assert result["signals_created"] == 1

    signals = service.get_signals(session=sqlite_session)
    assert signals[0].severity == "HIGH"


def test_duplicate_correlation_idempotency(sqlite_session: Session):
    """Test 9: Re-triggering correlation does not create duplicate signals or links."""
    service = SignalService()
    create_sample_anomaly(sqlite_session, service="payment-service", region="Pune")

    # 1st run: creates signal
    run1 = service.create_or_update_signals(session=sqlite_session)
    assert run1["signals_created"] == 1
    assert run1["anomalies_correlated"] == 1

    # 2nd run: no unlinked anomalies exist -> 0 created, 0 updated
    run2 = service.create_or_update_signals(session=sqlite_session)
    assert run2["signals_created"] == 0
    assert run2["signals_updated"] == 0
    assert run2["anomalies_correlated"] == 0

    signals = service.get_signals(session=sqlite_session)
    assert len(signals) == 1
    assert signals[0].related_anomalies_count == 1


def test_existing_open_signal_updated_on_subsequent_anomaly(sqlite_session: Session):
    """Test 10: An existing OPEN signal absorbs a new related anomaly arriving in a later batch."""
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    t1 = datetime(2026, 10, 5, 14, 5, 0, tzinfo=timezone.utc)

    # 1st anomaly arrives
    create_sample_anomaly(sqlite_session, metric="error_rate", severity="WARNING", time_window=t0)
    run1 = service.create_or_update_signals(session=sqlite_session)
    assert run1["signals_created"] == 1

    sig_before = service.get_signals(session=sqlite_session)[0]
    assert sig_before.title == "Payment Service Error Spike"
    assert sig_before.severity == "WARNING"

    # 2nd anomaly arrives 5 minutes later with latency + CRITICAL severity
    create_sample_anomaly(sqlite_session, metric="average_latency_ms", severity="CRITICAL", time_window=t1)
    run2 = service.create_or_update_signals(session=sqlite_session)
    assert run2["signals_created"] == 0
    assert run2["signals_updated"] == 1
    assert run2["anomalies_correlated"] == 1

    signals_after = service.get_signals(session=sqlite_session)
    assert len(signals_after) == 1
    sig_updated = signals_after[0]
    assert sig_updated.id == sig_before.id
    assert sig_updated.title == "Payment Service Degradation"
    assert sig_updated.severity == "CRITICAL"
    assert sig_updated.related_anomalies_count == 2
    assert ensure_utc(sig_updated.last_detected_at) == t1


# ==============================================================================
# 4. Signal API Endpoint Tests
# ==============================================================================

def test_api_signals_list_and_filters(sqlite_session: Session):
    """Test GET /api/signals with severity, status, and service filters."""
    app.dependency_overrides[get_db] = lambda: sqlite_session
    try:
        service = SignalService()
        create_sample_anomaly(sqlite_session, service="payment-service", severity="CRITICAL")
        create_sample_anomaly(sqlite_session, service="auth-service", severity="WARNING")
        service.create_or_update_signals(session=sqlite_session)

        # GET all signals
        res = client.get("/api/signals")
        assert res.status_code == 200
        data = res.json()
        assert len(data) == 2

        # Filter by service
        res_svc = client.get("/api/signals?service=payment-service")
        assert res_svc.status_code == 200
        assert len(res_svc.json()) == 1
        assert res_svc.json()[0]["service"] == "payment-service"

        # Filter by severity
        res_sev = client.get("/api/signals?severity=CRITICAL")
        assert res_sev.status_code == 200
        assert len(res_sev.json()) == 1
        assert res_sev.json()[0]["severity"] == "CRITICAL"

        # Filter by non-existent
        res_none = client.get("/api/signals?service=unknown-service")
        assert res_none.status_code == 200
        assert len(res_none.json()) == 0
    finally:
        app.dependency_overrides.clear()


def test_api_signal_detail_and_resolve_lifecycle(sqlite_session: Session):
    """Test 11 & 12: GET /api/signals/{id} returns anomalies and POST /resolve updates status."""
    app.dependency_overrides[get_db] = lambda: sqlite_session
    try:
        service = SignalService()
        t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
        t1 = datetime(2026, 10, 5, 14, 2, 0, tzinfo=timezone.utc)
        create_sample_anomaly(sqlite_session, metric="error_rate", severity="CRITICAL", time_window=t0)
        create_sample_anomaly(sqlite_session, metric="average_latency_ms", severity="CRITICAL", time_window=t1)
        service.create_or_update_signals(session=sqlite_session)

        signals = service.get_signals(session=sqlite_session)
        sig_id = signals[0].id

        # 1. Detail endpoint returns attached anomalies
        res_detail = client.get(f"/api/signals/{sig_id}")
        assert res_detail.status_code == 200
        detail_data = res_detail.json()
        assert detail_data["id"] == sig_id
        assert detail_data["status"] == "OPEN"
        assert detail_data["related_anomalies_count"] == 2
        assert len(detail_data["anomalies"]) == 2
        assert {a["metric"] for a in detail_data["anomalies"]} == {"error_rate", "average_latency_ms"}

        # 2. Resolve endpoint changes OPEN -> RESOLVED
        res_resolve = client.post(f"/api/signals/{sig_id}/resolve")
        assert res_resolve.status_code == 200
        resolved_data = res_resolve.json()
        assert resolved_data["id"] == sig_id
        assert resolved_data["status"] == "RESOLVED"
        assert len(resolved_data["anomalies"]) == 2  # Historical anomalies preserved

        # 3. Verify in query filter
        res_open = client.get("/api/signals?status=OPEN")
        assert len(res_open.json()) == 0

        res_resolved = client.get("/api/signals?status=RESOLVED")
        assert len(res_resolved.json()) == 1
        assert res_resolved.json()[0]["id"] == sig_id
    finally:
        app.dependency_overrides.clear()


def test_api_trigger_correlation_endpoint(sqlite_session: Session):
    """Test POST /api/signals/correlate endpoint."""
    app.dependency_overrides[get_db] = lambda: sqlite_session
    try:
        create_sample_anomaly(sqlite_session, service="checkout-service", severity="HIGH")

        response = client.post("/api/signals/correlate")
        assert response.status_code == 200
        data = response.json()
        assert data["signals_created"] == 1
        assert data["signals_updated"] == 0
        assert data["anomalies_correlated"] == 1
        assert len(data["signals"]) == 1
        assert data["signals"][0]["service"] == "checkout-service"
    finally:
        app.dependency_overrides.clear()


def test_already_resolved_signal_behavior(sqlite_session: Session):
    """
    Verify that resolving an already-resolved signal is safe/idempotent,
    and a new subsequent anomaly starts a new OPEN signal instead of updating the resolved one.
    """
    service = SignalService()
    t0 = datetime(2026, 10, 5, 14, 0, 0, tzinfo=timezone.utc)
    create_sample_anomaly(sqlite_session, service="billing-service", time_window=t0)
    service.create_or_update_signals(session=sqlite_session)

    open_sigs = service.get_signals(session=sqlite_session, status="OPEN")
    assert len(open_sigs) == 1
    sig_1 = open_sigs[0]

    # Resolve first signal
    resolved_sig = service.resolve_signal(signal_id=sig_1.id, session=sqlite_session)
    assert resolved_sig.status == "RESOLVED"

    # Resolving again is safe and idempotent
    resolved_again = service.resolve_signal(signal_id=sig_1.id, session=sqlite_session)
    assert resolved_again.status == "RESOLVED"

    # Subsequent anomaly for the same service arrives later
    t1 = datetime(2026, 10, 5, 14, 30, 0, tzinfo=timezone.utc)
    create_sample_anomaly(sqlite_session, service="billing-service", time_window=t1)
    service.create_or_update_signals(session=sqlite_session)

    # Must have 1 new OPEN signal, while the resolved signal stays intact
    all_sigs = service.get_signals(session=sqlite_session)
    assert len(all_sigs) == 2
    statuses = {s.id: s.status for s in all_sigs}
    assert statuses[sig_1.id] == "RESOLVED"
    new_sig = [s for s in all_sigs if s.id != sig_1.id][0]
    assert new_sig.status == "OPEN"

