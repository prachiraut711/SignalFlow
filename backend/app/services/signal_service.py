"""
Signal Correlation & Incident Management Service

Correlates individual metric anomalies into unified, higher-level operational
signals based on service, region, and sliding time-proximity windows.
"""

from datetime import datetime, timezone, timedelta
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.postgres import get_db, get_db_session
from app.models.anomaly import AnomalyRecord
from app.models.signal import SignalRecord, SignalAnomaly

logger = logging.getLogger(__name__)

SEVERITY_ORDER = {
    "INFO": 1,
    "WARNING": 2,
    "HIGH": 3,
    "CRITICAL": 4,
}

CORRELATION_WINDOW_SECONDS = 10 * 60  # 10 minutes


def format_service_name(service: str) -> str:
    """Format service identifier into Title Case, e.g. 'payment-service' -> 'Payment Service'."""
    return service.replace("-", " ").replace("_", " ").title()


def get_highest_severity(severities: List[str]) -> str:
    """Determine the highest operational severity level from a collection of severities."""
    if not severities:
        return "INFO"
    return max(severities, key=lambda s: SEVERITY_ORDER.get(str(s).upper(), 0))


def ensure_utc(dt: datetime) -> datetime:
    """Ensure a datetime object is timezone-aware and set to UTC."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def is_within_correlation_window(
    anomaly_time: datetime,
    signal_first: datetime,
    signal_last: datetime,
    max_delta_seconds: int = CORRELATION_WINDOW_SECONDS,
) -> bool:
    """
    Check if an anomaly timestamp falls within or near a signal's time range
    by less than or equal to max_delta_seconds (default 10 minutes).
    """
    anom_utc = ensure_utc(anomaly_time)
    first_utc = ensure_utc(signal_first)
    last_utc = ensure_utc(signal_last)

    if first_utc <= anom_utc <= last_utc:
        return True

    dist_to_last = abs((anom_utc - last_utc).total_seconds())
    dist_to_first = abs((anom_utc - first_utc).total_seconds())
    return min(dist_to_last, dist_to_first) <= max_delta_seconds


def generate_signal_title(anomalies: List[AnomalyRecord]) -> str:
    """
    Generate deterministic, human-readable signal title based on
    the combination of correlated anomaly metrics.
    """
    if not anomalies:
        return "Operational Incident"

    svc_name = format_service_name(anomalies[0].service)
    metrics = {a.metric for a in anomalies}

    has_error = "error_rate" in metrics
    has_latency = "average_latency_ms" in metrics
    has_traffic = "event_count" in metrics

    if has_error and has_latency:
        return f"{svc_name} Degradation"
    elif has_error:
        return f"{svc_name} Error Spike"
    elif has_latency:
        return f"{svc_name} Latency Degradation"
    elif has_traffic:
        return f"{svc_name} Traffic Anomaly"
    elif "composite" in metrics:
        return f"{svc_name} Performance Anomaly"
    else:
        return f"{svc_name} Operational Anomaly"


def generate_signal_description(
    service: str,
    region: str,
    anomalies: List[AnomalyRecord],
) -> str:
    """
    Generate a concise deterministic summary describing the operational incident.
    """
    svc_name = format_service_name(service)
    metrics = {a.metric for a in anomalies}
    has_error = "error_rate" in metrics
    has_latency = "average_latency_ms" in metrics
    has_traffic = "event_count" in metrics

    region_str = f"in {region}" if region and region.lower() != "global" else "globally"

    if has_error and has_latency:
        return f"{svc_name} {region_str} is experiencing elevated errors and latency."
    elif has_error:
        return f"{svc_name} {region_str} is experiencing an elevated error rate."
    elif has_latency:
        return f"{svc_name} {region_str} is experiencing abnormal latency degradation."
    elif has_traffic:
        return f"{svc_name} {region_str} is experiencing anomalous traffic volume."
    else:
        return f"{svc_name} {region_str} has detected operational deviations."


class SignalService:
    """
    Coordinates anomaly correlation, incident signal lifecycle (OPEN/RESOLVED),
    and signal querying.
    """

    def create_or_update_signals(
        self,
        session: Session,
        lookback_minutes: Optional[int] = None,
    ) -> Dict[str, Any]:
        """
        Scan unlinked anomalies and correlate them into new or existing OPEN signals.
        Idempotent: duplicate correlation runs will not create duplicate links or signals.
        """
        # 1. Identify anomalies that have not yet been attached to any signal
        linked_subquery = session.query(SignalAnomaly.anomaly_id).scalar_subquery()
        query = session.query(AnomalyRecord).filter(
            ~AnomalyRecord.id.in_(linked_subquery)
        )

        if lookback_minutes is not None:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=lookback_minutes)
            query = query.filter(AnomalyRecord.detected_at >= cutoff)

        unlinked_anomalies = query.order_by(
            AnomalyRecord.time_window.asc(),
            AnomalyRecord.id.asc()
        ).all()

        if not unlinked_anomalies:
            logger.info("No unlinked anomalies found for correlation.")
            return {
                "signals_created": 0,
                "signals_updated": 0,
                "anomalies_correlated": 0,
                "signals": [],
            }

        created_signals: Dict[int, SignalRecord] = {}
        updated_signals: Dict[int, SignalRecord] = {}
        anomalies_correlated_count = 0

        for anomaly in unlinked_anomalies:
            # Check candidate OPEN signals matching service and region
            candidate_signals = session.query(SignalRecord).filter(
                SignalRecord.service == anomaly.service,
                SignalRecord.region == anomaly.region,
                SignalRecord.status == "OPEN",
            ).order_by(SignalRecord.last_detected_at.desc()).all()

            matched_signal: Optional[SignalRecord] = None
            for cand in candidate_signals:
                if is_within_correlation_window(
                    anomaly.time_window,
                    cand.first_detected_at,
                    cand.last_detected_at,
                    max_delta_seconds=CORRELATION_WINDOW_SECONDS,
                ):
                    matched_signal = cand
                    break

            anom_time = ensure_utc(anomaly.time_window)

            if matched_signal is not None:
                # Correlate into existing OPEN signal
                already_linked = any(sa.anomaly_id == anomaly.id for sa in matched_signal.signal_anomalies)
                if not already_linked:
                    assoc = SignalAnomaly(signal_id=matched_signal.id, anomaly_id=anomaly.id)
                    session.add(assoc)
                    matched_signal.signal_anomalies.append(assoc)

                    # Update signal bounds and metadata
                    all_anomalies = matched_signal.anomalies + [anomaly]
                    matched_signal.last_detected_at = max(ensure_utc(matched_signal.last_detected_at), anom_time)
                    matched_signal.first_detected_at = min(ensure_utc(matched_signal.first_detected_at), anom_time)
                    matched_signal.severity = get_highest_severity([a.severity for a in all_anomalies])
                    matched_signal.title = generate_signal_title(all_anomalies)
                    matched_signal.description = generate_signal_description(
                        matched_signal.service,
                        matched_signal.region,
                        all_anomalies
                    )
                    matched_signal.updated_at = datetime.now(timezone.utc)
                    session.flush()

                    anomalies_correlated_count += 1
                    if matched_signal.id not in created_signals:
                        updated_signals[matched_signal.id] = matched_signal
            else:
                # Create a new OPEN signal
                now_utc = datetime.now(timezone.utc)
                ts_str = anom_time.strftime("%Y%m%d%H%M%S")
                sig_key = f"SIG-{anomaly.service}-{anomaly.region}-{ts_str}"

                # Ensure key uniqueness in case of simultaneous timestamps
                existing_key = session.query(SignalRecord).filter(SignalRecord.signal_key == sig_key).first()
                if existing_key:
                    sig_key = f"{sig_key}-{uuid.uuid4().hex[:6]}"

                new_signal = SignalRecord(
                    signal_key=sig_key,
                    title=generate_signal_title([anomaly]),
                    description=generate_signal_description(anomaly.service, anomaly.region, [anomaly]),
                    severity=anomaly.severity,
                    service=anomaly.service,
                    region=anomaly.region,
                    status="OPEN",
                    first_detected_at=anom_time,
                    last_detected_at=anom_time,
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                session.add(new_signal)
                session.flush()

                assoc = SignalAnomaly(signal_id=new_signal.id, anomaly_id=anomaly.id)
                session.add(assoc)
                new_signal.signal_anomalies.append(assoc)
                session.flush()

                anomalies_correlated_count += 1
                created_signals[new_signal.id] = new_signal

        session.commit()

        # Combine all affected signals for the response
        all_signals_map = {**created_signals, **updated_signals}
        return {
            "signals_created": len(created_signals),
            "signals_updated": len(updated_signals),
            "anomalies_correlated": anomalies_correlated_count,
            "signals": list(all_signals_map.values()),
        }

    def resolve_signal(self, signal_id: int, session: Session) -> Optional[SignalRecord]:
        """
        Transition an operational signal from OPEN to RESOLVED.
        Preserves all linked anomalies and history.
        """
        signal = session.query(SignalRecord).filter(SignalRecord.id == signal_id).first()
        if not signal:
            return None

        signal.status = "RESOLVED"
        signal.updated_at = datetime.now(timezone.utc)
        session.commit()
        session.refresh(signal)
        return signal

    def get_signals(
        self,
        session: Session,
        severity: Optional[str] = None,
        status: Optional[str] = None,
        service: Optional[str] = None,
        region: Optional[str] = None,
        limit: int = 50,
    ) -> List[SignalRecord]:
        """
        Retrieve incident signals from the relational platform store with filtering.
        """
        query = session.query(SignalRecord)
        if severity:
            query = query.filter(SignalRecord.severity == severity.upper())
        if status:
            query = query.filter(SignalRecord.status == status.upper())
        if service:
            query = query.filter(SignalRecord.service == service)
        if region:
            query = query.filter(SignalRecord.region == region)

        return query.order_by(
            SignalRecord.last_detected_at.desc(),
            SignalRecord.id.desc()
        ).limit(limit).all()

    def get_signal_by_id(self, signal_id: int, session: Session) -> Optional[SignalRecord]:
        """Retrieve a single signal by ID including its relationship associations."""
        return session.query(SignalRecord).filter(SignalRecord.id == signal_id).first()


def get_signal_service() -> SignalService:
    """FastAPI dependency provider returning a SignalService instance."""
    return SignalService()
