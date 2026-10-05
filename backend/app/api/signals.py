"""
Signal & Incident Management API Endpoints

Provides REST endpoints for retrieving aggregated operational signals,
triggering correlation scans across recent metric anomalies, and resolving incidents.
"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.signal import (
    SignalResponse,
    SignalDetailResponse,
    SignalCorrelationResponse,
)
from app.services.signal_service import SignalService, get_signal_service

router = APIRouter(prefix="/signals", tags=["Signals"])


@router.get(
    "",
    response_model=List[SignalResponse],
    summary="Get operational signals",
    description="Returns list of aggregated incident signals with optional filtering by severity, status, service, and region."
)
@router.get(
    "/",
    response_model=List[SignalResponse],
    include_in_schema=False
)
async def get_signals(
    severity: Optional[str] = Query(None, description="Filter by severity level (INFO, WARNING, HIGH, CRITICAL)"),
    status: Optional[str] = Query(None, description="Filter by status (OPEN, RESOLVED)"),
    service: Optional[str] = Query(None, description="Filter by service name"),
    region: Optional[str] = Query(None, description="Filter by region"),
    limit: int = Query(50, ge=1, le=500, description="Maximum signals to return"),
    signal_service: SignalService = Depends(get_signal_service),
    session: Session = Depends(get_db),
) -> List[SignalResponse]:
    """Retrieve filtered incident signals from the relational platform store."""
    records = signal_service.get_signals(
        session=session,
        severity=severity,
        status=status,
        service=service,
        region=region,
        limit=limit,
    )
    return [SignalResponse.model_validate(r) for r in records]


@router.post(
    "/correlate",
    response_model=SignalCorrelationResponse,
    status_code=status.HTTP_200_OK,
    summary="Trigger anomaly correlation scan",
    description="Correlates unlinked anomalies into new or existing OPEN signals using sliding time proximity."
)
async def trigger_correlation(
    lookback_minutes: Optional[int] = Query(None, description="Optional lookback window in minutes"),
    signal_service: SignalService = Depends(get_signal_service),
    session: Session = Depends(get_db),
) -> SignalCorrelationResponse:
    """Manually invoke the signal correlation pipeline."""
    result = signal_service.create_or_update_signals(
        session=session,
        lookback_minutes=lookback_minutes,
    )
    return SignalCorrelationResponse(
        signals_created=result["signals_created"],
        signals_updated=result["signals_updated"],
        anomalies_correlated=result["anomalies_correlated"],
        signals=[SignalResponse.model_validate(s) for s in result["signals"]],
    )


@router.get(
    "/{signal_id}",
    response_model=SignalDetailResponse,
    summary="Get signal details",
    description="Returns detailed signal information including all correlated raw anomalies."
)
async def get_signal_detail(
    signal_id: int,
    signal_service: SignalService = Depends(get_signal_service),
    session: Session = Depends(get_db),
) -> SignalDetailResponse:
    """Retrieve detailed signal metadata with attached anomaly records."""
    record = signal_service.get_signal_by_id(signal_id=signal_id, session=session)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal with ID {signal_id} not found"
        )
    return SignalDetailResponse.model_validate(record)


@router.post(
    "/{signal_id}/resolve",
    response_model=SignalDetailResponse,
    summary="Resolve operational signal",
    description="Transitions an open signal to RESOLVED while preserving full historical anomalies."
)
async def resolve_signal(
    signal_id: int,
    signal_service: SignalService = Depends(get_signal_service),
    session: Session = Depends(get_db),
) -> SignalDetailResponse:
    """Resolve an open operational incident signal."""
    record = signal_service.resolve_signal(signal_id=signal_id, session=session)
    if not record:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal with ID {signal_id} not found"
        )
    return SignalDetailResponse.model_validate(record)
