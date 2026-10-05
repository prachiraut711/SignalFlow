"""
Realistic Event Generator for SignalFlow Simulation
"""

from datetime import datetime, timedelta, timezone
import random
from typing import Any, Dict, Optional

from app.schemas.event import EventCreate, EventType
from app.simulator.scenarios import (
    SimulationScenario,
    SUPPORTED_REGIONS,
    SUPPORTED_SERVICES,
)


class EventGenerator:
    """
    Generates realistic, schema-valid synthetic events reflecting various operational scenarios.
    """

    def __init__(self):
        self._price_points = [99.0, 249.0, 499.0, 999.0, 1499.0, 2499.0, 4999.0]

    def _random_value(self) -> float:
        """Generate realistic transaction monetary value."""
        base = random.choice(self._price_points)
        cents = round(random.random() * 0.99, 2)
        return float(base + cents)

    def _random_user_id(self) -> str:
        """Generate random user identifier."""
        return f"user_{random.randint(1000, 9999)}"

    def _calculate_event_timestamp(
        self,
        progress: float,
        base_time: datetime,
    ) -> datetime:
        """
        Calculate realistic event timestamp ensuring distinct time-buckets for anomaly comparison:
        - Baseline phase (progress < 0.5): distributed across prior 2-minute baseline windows
        - Anomaly phase (progress >= 0.5): distributed within the active current 1-minute window
        """
        jitter = timedelta(seconds=random.uniform(-1.5, 1.5))
        if progress < 0.5:
            # Scale 0.0 -> 0.5 across (base_time - 120s) to base_time
            normalized = progress / 0.5
            offset_seconds = (normalized * 115.0) - 120.0
            return base_time + timedelta(seconds=offset_seconds) + jitter
        else:
            # Scale 0.5 -> 1.0 across base_time to (base_time + 55s)
            normalized = (progress - 0.5) / 0.5
            offset_seconds = normalized * 55.0
            return base_time + timedelta(seconds=offset_seconds) + jitter

    def generate_event(
        self,
        scenario: SimulationScenario,
        progress: float,
        service: Optional[str] = None,
        region: Optional[str] = None,
        base_time: Optional[datetime] = None,
    ) -> EventCreate:
        """
        Generate a single schema-valid application event conforming to scenario and phase.

        Args:
            scenario: Active simulation scenario enum
            progress: Float from 0.0 to 1.0 representing simulation completion
            service: Target service (optional override)
            region: Target region (optional override)
            base_time: Base reference datetime for windowing (defaults to now)

        Returns:
            EventCreate Pydantic instance ready for POST /api/events ingestion
        """
        now = base_time or datetime.now(timezone.utc)
        timestamp = self._calculate_event_timestamp(progress, now)
        is_anomaly_phase = progress >= 0.5
        phase_label = "anomaly" if is_anomaly_phase else "baseline"

        target_service = service or "payment-service"
        target_region = region or "Pune"

        # ---------------------------------------------------------------------
        # Scenario 1: NORMAL_TRAFFIC
        # ---------------------------------------------------------------------
        if scenario == SimulationScenario.NORMAL_TRAFFIC:
            target_service = service or random.choice(SUPPORTED_SERVICES)
            target_region = region or random.choice(SUPPORTED_REGIONS)
            event_type = random.choices(
                [
                    EventType.USER_LOGIN,
                    EventType.API_REQUEST,
                    EventType.ORDER_CREATED,
                    EventType.PAYMENT_SUCCESS,
                    EventType.NOTIFICATION_SENT,
                    EventType.USER_SIGNUP,
                ],
                weights=[25, 25, 20, 15, 10, 5],
            )[0]

            is_error = random.random() < 0.015  # 1.5% healthy error rate
            status_code = random.choice([400, 404]) if is_error else (201 if "create" in event_type.value or "signup" in event_type.value else 200)
            latency_ms = round(random.uniform(120.0, 420.0), 2)
            value = self._random_value() if event_type in (EventType.ORDER_CREATED, EventType.PAYMENT_SUCCESS) else 0.0

        # ---------------------------------------------------------------------
        # Scenario 2: PAYMENT_FAILURE_SPIKE
        # ---------------------------------------------------------------------
        elif scenario == SimulationScenario.PAYMENT_FAILURE_SPIKE:
            target_service = service or "payment-service"
            target_region = region or "Pune"

            if not is_anomaly_phase:
                # Baseline: 95% success, 5% failure, 300-500ms
                is_failed = random.random() < 0.05
                event_type = EventType.PAYMENT_FAILED if is_failed else EventType.PAYMENT_SUCCESS
                status_code = 500 if is_failed else 200
                latency_ms = round(random.uniform(280.0, 480.0), 2)
            else:
                # Anomaly: 30% failure, 2000-3200ms latency
                is_failed = random.random() < 0.30
                event_type = EventType.PAYMENT_FAILED if is_failed else EventType.PAYMENT_SUCCESS
                status_code = random.choice([500, 502, 504]) if is_failed else 200
                latency_ms = round(random.uniform(2100.0, 3200.0), 2)
            value = self._random_value()

        # ---------------------------------------------------------------------
        # Scenario 3: API_ERROR_SPIKE
        # ---------------------------------------------------------------------
        elif scenario == SimulationScenario.API_ERROR_SPIKE:
            target_service = service or "order-service"
            target_region = region or "Pune"

            if not is_anomaly_phase:
                is_err = random.random() < 0.02
                event_type = EventType.API_ERROR if is_err else EventType.API_REQUEST
                status_code = 500 if is_err else 200
                latency_ms = round(random.uniform(180.0, 390.0), 2)
            else:
                is_err = random.random() < 0.35
                event_type = EventType.API_ERROR if is_err else EventType.API_REQUEST
                status_code = random.choice([500, 502, 503]) if is_err else 200
                latency_ms = round(random.uniform(650.0, 1400.0), 2)
            value = 0.0

        # ---------------------------------------------------------------------
        # Scenario 4: HIGH_LATENCY
        # ---------------------------------------------------------------------
        elif scenario == SimulationScenario.HIGH_LATENCY:
            target_service = service or "order-service"
            target_region = region or "Pune"
            event_type = random.choice([EventType.API_REQUEST, EventType.ORDER_CREATED, EventType.PAYMENT_SUCCESS])

            if not is_anomaly_phase:
                status_code = 200
                latency_ms = round(random.uniform(250.0, 450.0), 2)
            else:
                # Latency spikes to 2200-4000ms while mostly returning HTTP 200
                status_code = 504 if random.random() < 0.05 else 200
                latency_ms = round(random.uniform(2200.0, 3900.0), 2)
            value = self._random_value() if event_type != EventType.API_REQUEST else 0.0

        # ---------------------------------------------------------------------
        # Scenario 5: TRAFFIC_SURGE
        # ---------------------------------------------------------------------
        elif scenario == SimulationScenario.TRAFFIC_SURGE:
            target_service = service or "order-service"
            target_region = region or "Pune"
            event_type = random.choice([EventType.API_REQUEST, EventType.ORDER_CREATED])
            is_err = random.random() < 0.02
            status_code = 500 if is_err else 200
            latency_ms = round(random.uniform(220.0, 480.0 if not is_anomaly_phase else 620.0), 2)
            value = self._random_value() if event_type == EventType.ORDER_CREATED else 0.0

        # ---------------------------------------------------------------------
        # Scenario 6: REGIONAL_FAILURE
        # ---------------------------------------------------------------------
        elif scenario == SimulationScenario.REGIONAL_FAILURE:
            target_service = service or "payment-service"
            focus_region = region or "Pune"

            if not is_anomaly_phase:
                target_region = random.choice(SUPPORTED_REGIONS)
                is_failed = random.random() < 0.03
                event_type = EventType.PAYMENT_FAILED if is_failed else EventType.PAYMENT_SUCCESS
                status_code = 500 if is_failed else 200
                latency_ms = round(random.uniform(250.0, 450.0), 2)
            else:
                # In anomaly phase, 50% traffic is directed to the affected region
                if random.random() < 0.5:
                    target_region = focus_region
                    is_failed = random.random() < 0.32
                    event_type = EventType.PAYMENT_FAILED if is_failed else EventType.PAYMENT_SUCCESS
                    status_code = random.choice([500, 502]) if is_failed else 200
                    latency_ms = round(random.uniform(2200.0, 3400.0), 2)
                else:
                    # Other regions remain healthy
                    other_regions = [r for r in SUPPORTED_REGIONS if r != focus_region]
                    target_region = random.choice(other_regions)
                    is_failed = random.random() < 0.02
                    event_type = EventType.PAYMENT_FAILED if is_failed else EventType.PAYMENT_SUCCESS
                    status_code = 500 if is_failed else 200
                    latency_ms = round(random.uniform(250.0, 450.0), 2)
            value = self._random_value()

        else:
            event_type = EventType.API_REQUEST
            status_code = 200
            latency_ms = 300.0
            value = 0.0

        return EventCreate(
            timestamp=timestamp,
            service=target_service,
            event_type=event_type,
            region=target_region,
            status_code=status_code,
            latency_ms=latency_ms,
            value=value,
            user_id=self._random_user_id(),
            metadata={
                "simulation": True,
                "scenario": scenario.value,
                "phase": phase_label,
            },
        )
