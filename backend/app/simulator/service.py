"""
Simulator Execution Service Module

Controls asynchronous simulation execution loops, enforces safety bounds,
and dispatches events through the production FastAPI ingestion endpoint (POST /api/events).
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Any, Dict, Optional
from fastapi import HTTPException, status
import httpx

from app.schemas.simulator import SimulatorStartRequest, SimulatorStatusResponse
from app.simulator.generator import EventGenerator
from app.simulator.scenarios import SimulationScenario, SCENARIO_METADATA
from app.workers.event_worker import EventWorker

logger = logging.getLogger(__name__)


class SimulatorService:
    """
    Manages state and lifecycle of the real-time event simulation loop.
    Enforces singleton active execution and sends events via POST /api/events.
    """

    MIN_EVENTS_PER_SECOND = 1
    MAX_EVENTS_PER_SECOND = 50
    MIN_DURATION_SECONDS = 5
    MAX_DURATION_SECONDS = 300

    def __init__(self, client: Optional[httpx.AsyncClient] = None):
        self._client = client
        self.generator = EventGenerator()
        self._running: bool = False
        self._task: Optional[asyncio.Task] = None
        self._stop_event = asyncio.Event()

        # Run Telemetry State
        self._current_scenario: Optional[SimulationScenario] = None
        self._events_generated: int = 0
        self._start_time: Optional[datetime] = None
        self._duration_seconds: int = 0
        self._events_per_second: int = 10
        self._service: Optional[str] = None
        self._region: Optional[str] = None
        self._elapsed_seconds: int = 0
        self._last_error: Optional[str] = None
        self._status_message: Optional[str] = None

    @property
    def is_running(self) -> bool:
        """Return whether a simulation is currently active."""
        return self._running

    def get_status(self) -> SimulatorStatusResponse:
        """Return current live or last completed status of the simulator."""
        elapsed = self._elapsed_seconds
        if self._running and self._start_time:
            elapsed = int((datetime.now(timezone.utc) - self._start_time).total_seconds())

        return SimulatorStatusResponse(
            running=self._running,
            scenario=self._current_scenario.value if self._current_scenario else None,
            events_generated=self._events_generated,
            elapsed_seconds=elapsed,
            duration_seconds=self._duration_seconds,
            events_per_second=self._events_per_second,
            service=self._service,
            region=self._region,
            message=self._status_message or ("Running" if self._running else "Idle"),
        )

    def start_simulation(self, config: SimulatorStartRequest) -> SimulatorStatusResponse:
        """
        Start a new event simulation run after validating safety limits and singleton state.
        """
        if self._running:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="A simulation is already actively running. Stop it before starting a new run.",
            )

        # Enforce safety limits
        if (
            config.events_per_second < self.MIN_EVENTS_PER_SECOND
            or config.events_per_second > self.MAX_EVENTS_PER_SECOND
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"events_per_second must be between {self.MIN_EVENTS_PER_SECOND} and {self.MAX_EVENTS_PER_SECOND}",
            )

        if (
            config.duration_seconds < self.MIN_DURATION_SECONDS
            or config.duration_seconds > self.MAX_DURATION_SECONDS
        ):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"duration_seconds must be between {self.MIN_DURATION_SECONDS} and {self.MAX_DURATION_SECONDS}",
            )

        meta = SCENARIO_METADATA.get(config.scenario, {})
        chosen_service = config.service or meta.get("default_service", "payment-service")
        chosen_region = config.region or meta.get("default_region", "Pune")

        # Initialize simulation run state
        self._running = True
        self._stop_event.clear()
        self._current_scenario = config.scenario
        self._duration_seconds = config.duration_seconds
        self._events_per_second = config.events_per_second
        self._service = chosen_service
        self._region = chosen_region
        self._events_generated = 0
        self._elapsed_seconds = 0
        self._start_time = datetime.now(timezone.utc)
        self._status_message = f"Simulation started: {config.scenario.value}"

        logger.info(
            f"Starting simulation [{config.scenario.value}] rate={config.events_per_second} eps, "
            f"duration={config.duration_seconds}s, service={chosen_service}, region={chosen_region}"
        )

        # Launch asynchronous simulation task
        self._task = asyncio.create_task(self._run_loop(config))
        return self.get_status()

    def stop_simulation(self) -> SimulatorStatusResponse:
        """
        Request immediate cancellation of the active simulation loop.
        """
        if not self._running:
            return self.get_status()

        logger.info("Stopping active simulation on user request...")
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()

        self._running = False
        self._status_message = "Simulation stopped by user."
        return self.get_status()

    async def _drain_stream_to_duckdb(self) -> int:
        """
        Drain any pending messages from Redis Streams to DuckDB via EventWorker.
        """
        worker = EventWorker()
        worker.is_running = True
        await worker.initialize_consumer_group()
        total_drained = 0
        try:
            worker.block_ms = 100
            while True:
                processed = await worker.process_batch()
                if processed == 0:
                    break
                total_drained += processed
        except Exception as exc:
            logger.warning(f"Could not drain worker batch to DuckDB: {exc}")
        return total_drained

    async def _run_loop(self, config: SimulatorStartRequest) -> None:
        """
        Internal simulation runner executing event generation and POSTing to /api/events.
        """
        from app.main import app

        base_time = datetime.now(timezone.utc)
        eps = float(config.events_per_second)
        interval = 1.0 / eps if eps > 0 else 0.1
        duration = float(config.duration_seconds)

        # Initialize transport for POST /api/events
        client = self._client
        owns_client = False
        if client is None:
            transport = httpx.ASGITransport(app=app)
            client = httpx.AsyncClient(transport=transport, base_url="http://localhost:8000")
            owns_client = True

        try:
            start_monotonic = asyncio.get_event_loop().time()

            while not self._stop_event.is_set():
                now_monotonic = asyncio.get_event_loop().time()
                elapsed = now_monotonic - start_monotonic
                self._elapsed_seconds = int(elapsed)

                if elapsed >= duration:
                    logger.info(f"Simulation duration of {duration}s reached. Completing run.")
                    break

                progress = min(1.0, elapsed / duration)

                # Dynamically adjust delay if in traffic surge scenario anomaly phase
                current_interval = interval
                if (
                    config.scenario == SimulationScenario.TRAFFIC_SURGE
                    and progress >= 0.5
                ):
                    current_interval = interval / 3.0  # 3x throughput surge

                # Generate valid event schema
                event = self.generator.generate_event(
                    scenario=config.scenario,
                    progress=progress,
                    service=self._service,
                    region=self._region,
                    base_time=base_time,
                )

                # POST event through the production endpoint
                try:
                    payload = event.model_dump(mode="json")
                    response = await client.post("/api/events", json=payload)
                    if response.status_code in (200, 201):
                        self._events_generated += 1
                        if self._events_generated % 25 == 0:
                            await self._drain_stream_to_duckdb()
                    else:
                        logger.warning(
                            f"Simulator event POST returned status {response.status_code}: {response.text}"
                        )
                except asyncio.CancelledError:
                    raise
                except Exception as post_exc:
                    logger.error(f"Simulator failed to POST event: {post_exc}")

                # Sleep until next event dispatch
                try:
                    await asyncio.sleep(current_interval)
                except asyncio.CancelledError:
                    break

        except asyncio.CancelledError:
            logger.info("Simulation task was cancelled.")
        finally:
            if owns_client and client is not None:
                await client.aclose()

            self._running = False
            self._status_message = (
                f"Simulation completed. Generated {self._events_generated} events."
            )
            logger.info(f"Simulation completed: {self._events_generated} events produced.")

            # Automatically drain queued stream events to DuckDB for instant availability
            drained = await self._drain_stream_to_duckdb()
            logger.info(f"Drained {drained} events from Redis Stream to DuckDB analytical store.")


# Singleton service instance
_simulator_service: Optional[SimulatorService] = None


def get_simulator_service() -> SimulatorService:
    """Dependency provider returning singleton SimulatorService instance."""
    global _simulator_service
    if _simulator_service is None:
        _simulator_service = SimulatorService()
    return _simulator_service
