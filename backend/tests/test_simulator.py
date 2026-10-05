"""
Automated Functional and Unit Tests for Simulator Module (Phase 8)
"""

import asyncio
from datetime import datetime, timezone
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.schemas.event import EventCreate, EventType
from app.schemas.simulator import SimulatorStartRequest, SimulatorStatusResponse
from app.simulator.generator import EventGenerator
from app.simulator.scenarios import SimulationScenario, SCENARIO_METADATA
from app.simulator.service import SimulatorService, get_simulator_service

client = TestClient(app)


# ==============================================================================
# 1. Generator Unit Tests
# ==============================================================================

def test_generator_valid_event_schema_all_scenarios():
    """Verify EventGenerator creates strictly valid EventCreate models across all scenarios."""
    generator = EventGenerator()
    now = datetime.now(timezone.utc)

    for scenario in SimulationScenario:
        # Test both baseline (progress=0.2) and anomaly (progress=0.8) phases
        for progress in [0.2, 0.8]:
            event = generator.generate_event(
                scenario=scenario,
                progress=progress,
                service="payment-service",
                region="Pune",
                base_time=now,
            )
            assert isinstance(event, EventCreate)
            assert event.service != ""
            assert event.region != ""
            assert event.status_code >= 100 and event.status_code <= 599
            assert event.latency_ms >= 0.0
            assert event.metadata.get("simulation") is True
            assert event.metadata.get("scenario") == scenario.value
            expected_phase = "anomaly" if progress >= 0.5 else "baseline"
            assert event.metadata.get("phase") == expected_phase


def test_generator_payment_failure_spike_characteristics():
    """Verify payment failure spike transitions from healthy baseline to high errors and latency."""
    generator = EventGenerator()
    now = datetime.now(timezone.utc)

    # Sample 100 baseline events
    baseline_events = [
        generator.generate_event(SimulationScenario.PAYMENT_FAILURE_SPIKE, progress=0.25, base_time=now)
        for _ in range(100)
    ]
    # Sample 100 anomaly events
    anomaly_events = [
        generator.generate_event(SimulationScenario.PAYMENT_FAILURE_SPIKE, progress=0.75, base_time=now)
        for _ in range(100)
    ]

    baseline_errors = sum(1 for e in baseline_events if e.event_type == EventType.PAYMENT_FAILED or e.status_code >= 400)
    anomaly_errors = sum(1 for e in anomaly_events if e.event_type == EventType.PAYMENT_FAILED or e.status_code >= 400)

    avg_baseline_latency = sum(e.latency_ms for e in baseline_events) / len(baseline_events)
    avg_anomaly_latency = sum(e.latency_ms for e in anomaly_events) / len(anomaly_events)

    # Baseline should have very few errors and lower latency
    assert baseline_errors < 15
    assert avg_baseline_latency < 600.0

    # Anomaly phase should have significant error count and high latency (> 1800ms)
    assert anomaly_errors >= 18
    assert anomaly_errors > baseline_errors
    assert avg_anomaly_latency > 1800.0


def test_generator_high_latency_characteristics():
    """Verify high latency scenario produces slow responses while maintaining mostly HTTP 200."""
    generator = EventGenerator()
    now = datetime.now(timezone.utc)

    anomaly_events = [
        generator.generate_event(SimulationScenario.HIGH_LATENCY, progress=0.8, base_time=now)
        for _ in range(30)
    ]

    avg_latency = sum(e.latency_ms for e in anomaly_events) / len(anomaly_events)
    assert avg_latency > 2000.0
    status_200_count = sum(1 for e in anomaly_events if e.status_code == 200)
    assert status_200_count >= 25  # predominantly HTTP 200


def test_generator_regional_failure_characteristics():
    """Verify regional failure concentrates degradation in the target region."""
    generator = EventGenerator()
    now = datetime.now(timezone.utc)

    # Generate events during anomaly phase for target region Pune
    anomaly_events = [
        generator.generate_event(SimulationScenario.REGIONAL_FAILURE, progress=0.8, region="Pune", base_time=now)
        for _ in range(60)
    ]

    pune_events = [e for e in anomaly_events if e.region == "Pune"]
    other_events = [e for e in anomaly_events if e.region != "Pune"]

    assert len(pune_events) > 0
    assert len(other_events) > 0

    pune_errors = sum(1 for e in pune_events if e.status_code >= 400)
    other_errors = sum(1 for e in other_events if e.status_code >= 400)

    pune_error_rate = pune_errors / len(pune_events)
    other_error_rate = other_errors / len(other_events)

    assert pune_error_rate > other_error_rate


# ==============================================================================
# 2. Simulator API Functional Tests
# ==============================================================================

def test_api_simulator_scenarios_catalog():
    """Verify GET /api/simulator/scenarios returns all metadata and defaults."""
    response = client.get("/api/simulator/scenarios")
    assert response.status_code == 200
    data = response.json()
    assert "scenarios" in data
    assert len(data["scenarios"]) == len(SimulationScenario)
    assert "supported_services" in data
    assert "supported_regions" in data


def test_api_simulator_status_initially_idle():
    """Verify GET /api/simulator/status returns idle state when not running."""
    sim_service = get_simulator_service()
    sim_service.stop_simulation()

    response = client.get("/api/simulator/status")
    assert response.status_code == 200
    data = response.json()
    assert data["running"] is False
    assert "events_generated" in data


def test_api_simulator_invalid_events_per_second():
    """Verify POST /api/simulator/start rejects out-of-bounds events_per_second."""
    # Test EPS < 1
    res_low = client.post("/api/simulator/start", json={
        "scenario": "normal_traffic",
        "events_per_second": 0,
        "duration_seconds": 30,
    })
    assert res_low.status_code == 422

    # Test EPS > 50
    res_high = client.post("/api/simulator/start", json={
        "scenario": "normal_traffic",
        "events_per_second": 51,
        "duration_seconds": 30,
    })
    assert res_high.status_code == 422


def test_api_simulator_invalid_duration_seconds():
    """Verify POST /api/simulator/start rejects out-of-bounds duration_seconds."""
    # Test duration < 5s
    res_low = client.post("/api/simulator/start", json={
        "scenario": "normal_traffic",
        "events_per_second": 10,
        "duration_seconds": 4,
    })
    assert res_low.status_code == 422

    # Test duration > 300s
    res_high = client.post("/api/simulator/start", json={
        "scenario": "normal_traffic",
        "events_per_second": 10,
        "duration_seconds": 301,
    })
    assert res_high.status_code == 422


def test_api_simulator_lifecycle_start_and_stop():
    """Verify starting a simulation, preventing duplicate run, and stopping cleanly."""
    sim_service = get_simulator_service()
    sim_service.stop_simulation()

    with TestClient(app) as tc:
        # 1. Start a simulation
        start_payload = {
            "scenario": "payment_failure_spike",
            "events_per_second": 5,
            "duration_seconds": 20,
            "service": "payment-service",
            "region": "Pune",
        }
        res_start = tc.post("/api/simulator/start", json=start_payload)
        assert res_start.status_code == 200
        data_start = res_start.json()
        assert data_start["running"] is True
        assert data_start["scenario"] == "payment_failure_spike"

        # 2. Attempt duplicate start while running -> Expect 400
        res_dup = tc.post("/api/simulator/start", json=start_payload)
        assert res_dup.status_code == 400
        assert "already actively running" in res_dup.json()["detail"]

        # 3. Check status is running
        res_status = tc.get("/api/simulator/status")
        assert res_status.status_code == 200
        assert res_status.json()["running"] is True

        # 4. Stop simulation cleanly
        res_stop = tc.post("/api/simulator/stop")
        assert res_stop.status_code == 200
        data_stop = res_stop.json()
        assert data_stop["running"] is False

        # 5. Verify status reflects stopped
        res_final = tc.get("/api/simulator/status")
        assert res_final.json()["running"] is False
