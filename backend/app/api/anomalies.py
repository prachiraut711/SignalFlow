"""
Anomaly Detection API Endpoints

Provides endpoints for retrieving detected operational anomalies and
triggering detection scans across recent analytical windows.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.anomaly import AnomalyResponse, DetectionRunResponse
from app.services.anomaly_service import AnomalyService, get_anomaly_service

router = APIRouter(prefix="/anomalies", tags=["Anomalies"])


@router.get(
    "",
    response_model=List[AnomalyResponse],
    summary="Get detected anomalies",
    description="Returns list of detected metric anomalies with optional filtering by service and severity."
)
@router.get(
    "/",
    response_model=List[AnomalyResponse],
    include_in_schema=False
)
async def get_anomalies(
    service: Optional[str] = Query(None, description="Filter by service name"),
    severity: Optional[str] = Query(None, description="Filter by severity level (INFO, WARNING, HIGH, CRITICAL)"),
    limit: int = Query(50, ge=1, le=500, description="Maximum anomalies to return"),
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    session: Session = Depends(get_db),
) -> List[AnomalyResponse]:
    """Retrieve filtered anomaly records from the persistent platform store."""
    records = anomaly_service.get_anomalies(
        service=service,
        severity=severity,
        limit=limit,
        session=session,
    )
    return [AnomalyResponse.model_validate(r) for r in records]


@router.post(
    "/detect",
    response_model=DetectionRunResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger anomaly detection scan",
    description="Scans recent DuckDB analytical windows against baselines and records new anomalies."
)
async def trigger_detection(
    anomaly_service: AnomalyService = Depends(get_anomaly_service),
    session: Session = Depends(get_db),
) -> DetectionRunResponse:
    """Manually invoke the dual-layer anomaly detection pipeline."""
    result = anomaly_service.run_anomaly_detection(session=session)
    return DetectionRunResponse(
        windows_evaluated=result.get("services_scanned", 0),
        anomalies_detected=result.get("anomalies_detected", 0),
        anomalies_persisted=result.get("anomalies_persisted", 0),
        anomalies=[AnomalyResponse.model_validate(r) for r in result.get("anomalies", [])],
    )
