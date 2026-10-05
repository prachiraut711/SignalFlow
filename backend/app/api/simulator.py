"""
Simulator API Endpoints

Provides REST control endpoints for launching, stopping, and inspecting
realistic event simulation runs.
"""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.simulator import SimulatorStartRequest, SimulatorStatusResponse
from app.services.anomaly_service import AnomalyService, get_anomaly_service
from app.services.signal_service import SignalService, get_signal_service
from app.simulator.scenarios import SimulationScenario, SCENARIO_METADATA, SUPPORTED_REGIONS, SUPPORTED_SERVICES
from app.simulator.service import SimulatorService, get_simulator_service

router = APIRouter(prefix="/simulator", tags=["Simulator"])


@router.post(
    "/start",
    response_model=SimulatorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Start event simulation",
    description="Begins a background simulation loop generating realistic telemetry and POSTing to /api/events."
)
async def start_simulation(
    request: SimulatorStartRequest,
    simulator_service: SimulatorService = Depends(get_simulator_service),
) -> SimulatorStatusResponse:
    """Launch a single active simulation session."""
    return simulator_service.start_simulation(request)


@router.post(
    "/stop",
    response_model=SimulatorStatusResponse,
    status_code=status.HTTP_200_OK,
    summary="Stop active simulation",
    description="Immediately cancels the running simulation task."
)
async def stop_simulation(
    simulator_service: SimulatorService = Depends(get_simulator_service),
) -> SimulatorStatusResponse:
    """Halt the active simulation loop."""
    return simulator_service.stop_simulation()


@router.get(
    "/status",
    response_model=SimulatorStatusResponse,
    summary="Get simulator status",
    description="Returns whether a simulation is running, elapsed seconds, and total events generated."
)
async def get_simulator_status(
    simulator_service: SimulatorService = Depends(get_simulator_service),
) -> SimulatorStatusResponse:
    """Query live execution telemetry of the simulator."""
    return simulator_service.get_status()


@router.get(
    "/scenarios",
    summary="List supported scenarios",
    description="Returns metadata and defaults for all supported simulation scenarios."
)
async def list_scenarios() -> Dict[str, Any]:
    """Retrieve metadata catalog of all available simulation scenarios."""
    scenarios_list = []
    for scenario_enum, meta in SCENARIO_METADATA.items():
        scenarios_list.append({
            "id": scenario_enum.value,
            "title": meta["title"],
            "description": meta["description"],
            "default_service": meta["default_service"],
            "default_region": meta["default_region"],
            "expected_anomaly": meta["expected_anomaly"],
        })
    return {
        "scenarios": scenarios_list,
        "supported_services": SUPPORTED_SERVICES,
        "supported_regions": SUPPORTED_REGIONS,
    }


@router.post(
    "/evaluate",
    summary="Run post-simulation pipeline scan",
    description="Convenience orchestration endpoint to trigger anomaly detection and signal correlation sequentially."
)
async def run_pipeline_evaluation(
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    signal_service: SignalService = Depends(get_signal_service),
    session: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Run detection and correlation passes across newly ingested simulation data.
    """
    detect_res = anomaly_service.run_anomaly_detection(session=session)
    correlate_res = signal_service.create_or_update_signals(session=session)
    return {
        "anomalies_detected": detect_res.get("detected_count", 0),
        "signals_created": correlate_res.get("signals_created", 0),
        "signals_updated": correlate_res.get("signals_updated", 0),
    }
