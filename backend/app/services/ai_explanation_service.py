"""
AI Incident Explanation Service Module

Leverages OpenRouter (OpenAI-compatible HTTP chat completions) to generate
concise, structured incident diagnostic summaries, likely hypotheses, and
recommended operational remediation actions.
"""

from datetime import datetime, timezone
import json
import logging
from typing import Any, Dict, List, Optional
from fastapi import Depends
import httpx

from app.config import get_settings
from app.models.signal import SignalRecord
from app.schemas.ai_explanation import AIExplanationResponse

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = (
    "You are an incident analysis assistant for an enterprise observability platform.\n"
    "Analyze only the telemetry provided.\n"
    "Do not invent metrics or facts.\n"
    "Clearly distinguish observed facts from possible causes.\n"
    "Never state that a potential cause is confirmed; frame them as possibilities.\n"
    "Return concise operational guidance suitable for a software engineer.\n"
    "You must reply with valid JSON only conforming to this exact structure:\n"
    "{\n"
    '  "summary": "2-3 sentences summarizing the operational event",\n'
    '  "likely_causes": ["2-4 plausible causes (hypotheses, not confirmed facts)"],\n'
    '  "recommended_actions": ["3-5 concrete operational verification and remediation steps"]\n'
    "}"
)


class OpenRouterConfigError(Exception):
    """Raised when OpenRouter API key is missing or not configured."""
    pass


class OpenRouterServiceError(Exception):
    """Raised when OpenRouter call fails, times out, or returns invalid output."""
    pass


def build_incident_prompt(signal: SignalRecord) -> str:
    """
    Construct a controlled, structured telemetry context prompt for the LLM.
    Contains strictly observed telemetry and metric anomalies without speculation.
    """
    anomalies_lines = []
    for anom in signal.anomalies:
        z_str = f"{anom.z_score:.2f}" if anom.z_score is not None else "N/A"
        iso_str = f"{anom.isolation_score:.3f}" if anom.isolation_score is not None else "N/A"
        block = (
            f"- Metric: {anom.metric} (Anomaly Type: {anom.anomaly_type})\n"
            f"  Current Value: {anom.current_value}\n"
            f"  Baseline Value: {anom.baseline_value}\n"
            f"  Percentage Change: {anom.percentage_change:+.2f}%\n"
            f"  Z-Score: {z_str}\n"
            f"  Isolation Score: {iso_str}\n"
            f"  Severity: {anom.severity}\n"
            f"  Diagnostic Detail: {anom.reason}"
        )
        anomalies_lines.append(block)

    anomalies_text = "\n".join(anomalies_lines) if anomalies_lines else "No individual metric anomalies attached."

    prompt = (
        f"Incident Context:\n"
        f"Signal Title: {signal.title}\n"
        f"Severity: {signal.severity}\n"
        f"Service: {signal.service}\n"
        f"Region: {signal.region}\n"
        f"Status: {signal.status}\n"
        f"First Detected At: {signal.first_detected_at}\n"
        f"Last Detected At: {signal.last_detected_at}\n\n"
        f"Correlated Metric Telemetry:\n{anomalies_text}\n\n"
        f"Provide concise operational guidance in the requested JSON structure."
    )
    return prompt


def clean_json_response(raw_text: str) -> str:
    """Strip markdown code fences and extraneous whitespace from model response."""
    text = raw_text.strip()
    if text.startswith("```json"):
        text = text[7:]
    elif text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    return text.strip()


class AIExplanationService:
    """
    Service responsible for querying OpenRouter and returning structured incident explanations.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        base_url: Optional[str] = None,
        timeout: float = 25.0,
        http_client: Optional[httpx.AsyncClient] = None,
    ):
        settings = get_settings()
        self.api_key = api_key if api_key is not None else settings.OPENROUTER_API_KEY
        self.model = model or settings.OPENROUTER_MODEL
        self.base_url = (base_url or settings.OPENROUTER_BASE_URL).rstrip("/")
        self.timeout = timeout
        self.http_client = http_client

    async def generate_incident_explanation(self, signal: SignalRecord) -> AIExplanationResponse:
        """
        Send structured incident telemetry to OpenRouter and parse the returned explanation.
        """
        # 1. Verify API Key
        if not self.api_key or not self.api_key.strip():
            logger.warning("OpenRouter API key is not configured.")
            raise OpenRouterConfigError("OpenRouter API key is not configured.")

        # 2. Build Prompt
        user_prompt = build_incident_prompt(signal)
        endpoint = f"{self.base_url}/chat/completions"

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/SignalFlow",
            "X-Title": "SignalFlow",
        }

        payload: Dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
        }

        # 3. Call OpenRouter
        try:
            if self.http_client is not None:
                response = await self.http_client.post(
                    endpoint,
                    json=payload,
                    headers=headers,
                    timeout=self.timeout
                )
            else:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(
                        endpoint,
                        json=payload,
                        headers=headers
                    )

            response.raise_for_status()
            data = response.json()

        except httpx.TimeoutException as exc:
            logger.error(f"OpenRouter API call timed out after {self.timeout}s: {exc.__class__.__name__}")
            raise OpenRouterServiceError("AI explanation service request timed out.")
        except httpx.HTTPStatusError as exc:
            logger.error(f"OpenRouter API returned HTTP {exc.response.status_code}")
            raise OpenRouterServiceError("AI explanation service is temporarily unavailable.")
        except httpx.RequestError as exc:
            logger.error(f"OpenRouter network connectivity error: {exc.__class__.__name__}")
            raise OpenRouterServiceError("AI explanation service is temporarily unavailable.")
        except Exception as exc:
            logger.error(f"Unexpected error communicating with OpenRouter: {exc.__class__.__name__}")
            raise OpenRouterServiceError("AI explanation service is temporarily unavailable.")

        # 4. Parse Structured Model Response
        try:
            choices = data.get("choices", [])
            if not choices or not choices[0].get("message", {}).get("content"):
                raise OpenRouterServiceError("Model response was empty or malformed.")

            raw_content = choices[0]["message"]["content"]
            cleaned_json = clean_json_response(raw_content)
            parsed = json.loads(cleaned_json)

            summary = str(parsed.get("summary", "")).strip()
            likely_causes = [str(c).strip() for c in parsed.get("likely_causes", []) if str(c).strip()]
            recommended_actions = [str(a).strip() for a in parsed.get("recommended_actions", []) if str(a).strip()]

            if not summary or not likely_causes or not recommended_actions:
                raise OpenRouterServiceError("Model response was missing required fields.")

        except json.JSONDecodeError as exc:
            logger.error(f"Failed to parse OpenRouter response as JSON: {exc}")
            raise OpenRouterServiceError("Failed to parse AI explanation response.")
        except OpenRouterServiceError:
            raise
        except Exception as exc:
            logger.error(f"Error parsing OpenRouter response: {exc.__class__.__name__}")
            raise OpenRouterServiceError("Failed to parse AI explanation response.")

        return AIExplanationResponse(
            signal_id=signal.id,
            summary=summary,
            likely_causes=likely_causes,
            recommended_actions=recommended_actions,
            model=self.model,
            generated_at=datetime.now(timezone.utc),
        )


def get_ai_explanation_service() -> AIExplanationService:
    """FastAPI dependency provider for AIExplanationService."""
    return AIExplanationService()
