"""
AI Explanation API Endpoints

Provides REST endpoints for generating on-demand AI diagnostic explanations
for detected operational incident signals using OpenRouter.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.postgres import get_db
from app.schemas.ai_explanation import AIExplanationResponse
from app.services.ai_explanation_service import (
    AIExplanationService,
    OpenRouterConfigError,
    OpenRouterServiceError,
    get_ai_explanation_service,
)
from app.services.signal_service import SignalService, get_signal_service

router = APIRouter(prefix="/signals", tags=["AI Explanation"])


@router.post(
    "/{signal_id}/explain",
    response_model=AIExplanationResponse,
    status_code=status.HTTP_200_OK,
    summary="Generate AI incident explanation",
    description="Invokes OpenRouter LLM to analyze correlated signal telemetry and return actionable diagnostic guidance."
)
async def explain_signal_incident(
    signal_id: int,
    signal_service: SignalService = Depends(get_signal_service),
    ai_service: AIExplanationService = Depends(get_ai_explanation_service),
    session: Session = Depends(get_db),
) -> AIExplanationResponse:
    """
    Generate an AI-driven operational diagnostic analysis for an incident signal.
    """
    # 1. Retrieve the signal and its correlated anomalies
    signal = signal_service.get_signal_by_id(signal_id=signal_id, session=session)
    if not signal:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Signal with ID {signal_id} not found"
        )

    # 2. Invoke OpenRouter through the AI service
    try:
        explanation = await ai_service.generate_incident_explanation(signal=signal)
        return explanation
    except OpenRouterConfigError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc) or "OpenRouter API key is not configured."
        )
    except OpenRouterServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc) or "AI explanation service is temporarily unavailable."
        )
