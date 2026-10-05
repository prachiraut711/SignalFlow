"""
Anomaly Detection & Evaluation Service Module

Orchestrates time-window aggregation retrieval from DuckDB, baseline calculations,
dual-layer detection (Statistical + Isolation Forest), deduplication, and persistence
to PostgreSQL.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.duckdb import DuckDBService, get_duckdb_service
from app.db.postgres import get_db, get_db_session
from app.models.anomaly import AnomalyRecord
from app.ml.statistical_detector import detect_statistical_anomaly
from app.ml.anomaly_detector import IsolationForestDetector

logger = logging.getLogger(__name__)


class AnomalyService:
    """
    Coordinates anomaly detection pipelines across time-window metrics.
    """

    def __init__(
        self,
        duckdb_service: Optional[DuckDBService] = None,
        db_session: Optional[Session] = None,
    ):
        self.duckdb_service = duckdb_service or get_duckdb_service()
        self.db_session = db_session

    def get_service_windows(self, service: str) -> List[Dict[str, Any]]:
        """
        Retrieve chronological 1-minute metric windows for a service from DuckDB.
        """
        query = """
        SELECT 
            time_bucket(INTERVAL '1 minute', timestamp::TIMESTAMP) AS time_window,
            service,
            region,
            COUNT(*) AS event_count,
            SUM(CASE WHEN status_code >= 400 OR event_type IN ('payment_failed', 'api_error') THEN 1 ELSE 0 END) AS error_count,
            AVG(latency_ms) AS average_latency_ms
        FROM events
        WHERE service = ?
        GROUP BY time_window, service, region
        ORDER BY time_window ASC
        """
        rows = self.duckdb_service.query(query, (service,))
        windows = []
        for r in rows:
            event_count = int(r[3])
            error_count = int(r[4] or 0)
            error_rate = round((error_count / event_count) * 100.0, 2) if event_count > 0 else 0.0
            avg_latency = round(float(r[5] or 0.0), 2)
            windows.append({
                "time_window": r[0],
                "service": str(r[1]),
                "region": str(r[2]),
                "event_count": event_count,
                "error_count": error_count,
                "error_rate": error_rate,
                "average_latency_ms": avg_latency,
            })
        return windows

    def get_all_services(self) -> List[str]:
        """Fetch distinct services from DuckDB analytical events."""
        query = "SELECT DISTINCT service FROM events ORDER BY service"
        rows = self.duckdb_service.query(query)
        return [str(r[0]) for r in rows]

    def detect_anomalies_for_service(
        self,
        service: str,
        session: Session,
    ) -> List[AnomalyRecord]:
        """
        Execute dual-layer anomaly detection (Statistical + Isolation Forest)
        for a single service.
        """
        windows = self.get_service_windows(service)
        if len(windows) < 2:
            logger.info(
                f"Service '{service}' has only {len(windows)} window(s). Need >= 2 to establish baseline."
            )
            return []

        # Current evaluation window is the most recent
        current_window = windows[-1]
        time_window = current_window["time_window"]
        region = current_window["region"]

        # Baseline comprises all prior consecutive windows (up to 30)
        baseline_windows = windows[:-1][-30:]

        # 1. Run Machine Learning (Isolation Forest) on composite feature vectors
        iso_detector = IsolationForestDetector()
        iso_result = iso_detector.detect(baseline_windows, current_window)
        isolation_score = iso_result.get("isolation_score")

        detected_records: List[AnomalyRecord] = []
        metrics_to_test = ["error_rate", "average_latency_ms", "event_count"]

        stat_anomaly_found = False

        # 2. Run Statistical Detection on each individual metric
        for metric in metrics_to_test:
            current_val = float(current_window[metric])
            baseline_vals = [float(w[metric]) for w in baseline_windows]

            stat_res = detect_statistical_anomaly(
                metric=metric,
                current_value=current_val,
                baseline_values=baseline_vals,
            )

            if stat_res:
                stat_anomaly_found = True
                # Deduplication check: check if anomaly already persisted for (service, region, time_window, metric)
                existing = session.query(AnomalyRecord).filter(
                    AnomalyRecord.service == service,
                    AnomalyRecord.region == region,
                    AnomalyRecord.time_window == time_window,
                    AnomalyRecord.metric == metric,
                ).first()

                if not existing:
                    anomaly_rec = AnomalyRecord(
                        detected_at=datetime.now(timezone.utc),
                        time_window=time_window,
                        service=service,
                        region=region,
                        metric=metric,
                        anomaly_type=stat_res["anomaly_type"],
                        current_value=stat_res["current_value"],
                        baseline_value=stat_res["baseline_value"],
                        percentage_change=stat_res["percentage_change"],
                        z_score=stat_res["z_score"],
                        isolation_score=isolation_score,
                        severity=stat_res["severity"],
                        reason=stat_res["reason"],
                    )
                    session.add(anomaly_rec)
                    detected_records.append(anomaly_rec)

        # 3. If Isolation Forest flagged outlier but no statistical metric fired:
        if iso_result.get("is_anomaly") and not stat_anomaly_found:
            existing = session.query(AnomalyRecord).filter(
                AnomalyRecord.service == service,
                AnomalyRecord.region == region,
                AnomalyRecord.time_window == time_window,
                AnomalyRecord.metric == "composite",
            ).first()

            if not existing:
                anomaly_rec = AnomalyRecord(
                    detected_at=datetime.now(timezone.utc),
                    time_window=time_window,
                    service=service,
                    region=region,
                    metric="composite",
                    anomaly_type="multivariate_anomaly",
                    current_value=float(current_window["error_rate"]),
                    baseline_value=float(sum(w["error_rate"] for w in baseline_windows) / len(baseline_windows)),
                    percentage_change=0.0,
                    z_score=None,
                    isolation_score=isolation_score,
                    severity="WARNING",
                    reason=f"Isolation Forest identified abnormal multidimensional telemetry pattern (score: {isolation_score})",
                )
                session.add(anomaly_rec)
                detected_records.append(anomaly_rec)

        return detected_records

    def run_anomaly_detection(self, session: Optional[Session] = None) -> Dict[str, Any]:
        """
        Scan all services in DuckDB, calculate baselines, and persist new anomalies.
        """
        services = self.get_all_services()
        total_detected = 0
        all_new_anomalies: List[AnomalyRecord] = []

        if session is not None:
            for s in services:
                new_recs = self.detect_anomalies_for_service(s, session)
                all_new_anomalies.extend(new_recs)
            session.commit()
            total_detected = len(all_new_anomalies)
        else:
            with get_db_session() as s:
                for service in services:
                    new_recs = self.detect_anomalies_for_service(service, s)
                    all_new_anomalies.extend(new_recs)
                total_detected = len(all_new_anomalies)

        return {
            "services_scanned": len(services),
            "anomalies_detected": total_detected,
            "anomalies_persisted": total_detected,
            "anomalies": all_new_anomalies,
        }

    def get_anomalies(
        self,
        service: Optional[str] = None,
        severity: Optional[str] = None,
        limit: int = 50,
        session: Optional[Session] = None,
    ) -> List[AnomalyRecord]:
        """
        Query persistent anomaly records from PostgreSQL with filtering.
        """
        def _execute(s: Session):
            query = s.query(AnomalyRecord)
            if service:
                query = query.filter(AnomalyRecord.service == service)
            if severity:
                query = query.filter(AnomalyRecord.severity == severity.upper())
            return query.order_by(AnomalyRecord.detected_at.desc(), AnomalyRecord.id.desc()).limit(limit).all()

        if session is not None:
            return _execute(session)
        with get_db_session() as s:
            return _execute(s)


def get_anomaly_service(
    duckdb_service: DuckDBService = Depends(get_duckdb_service),
    db_session: Session = Depends(get_db),
) -> AnomalyService:
    """FastAPI dependency provider returning an AnomalyService instance."""
    return AnomalyService(duckdb_service=duckdb_service, db_session=db_session)
