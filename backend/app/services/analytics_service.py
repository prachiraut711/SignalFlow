"""
Analytics Query & Aggregation Service Module

Executes analytical aggregations, metric calculations, and time-window rollups
directly against DuckDB's in-process columnar store.
"""

import logging
from typing import List, Optional
from fastapi import Depends

from app.db.duckdb import DuckDBService, get_duckdb_service
from app.schemas.analytics import (
    AnalyticsOverviewResponse,
    ServiceMetricItem,
    TimeWindowMetricItem,
)

logger = logging.getLogger(__name__)


class AnalyticsService:
    """
    Service providing high-speed analytical queries on normalized events.
    """

    def __init__(self, duckdb_service: Optional[DuckDBService] = None):
        self.duckdb_service = duckdb_service or get_duckdb_service()

    def get_event_count(self) -> int:
        """Return total number of events recorded in the analytical store."""
        query = "SELECT COUNT(*) FROM events"
        rows = self.duckdb_service.query(query)
        return int(rows[0][0]) if rows and rows[0][0] is not None else 0

    def get_error_count(self) -> int:
        """Return total number of error events (status >= 400 or failure types)."""
        query = """
        SELECT COUNT(*) 
        FROM events 
        WHERE status_code >= 400 
           OR event_type IN ('payment_failed', 'api_error', 'order_cancelled')
        """
        rows = self.duckdb_service.query(query)
        return int(rows[0][0]) if rows and rows[0][0] is not None else 0

    def get_error_rate(self) -> float:
        """Calculate overall platform error percentage (0.0 to 100.0)."""
        total = self.get_event_count()
        if total == 0:
            return 0.0
        errors = self.get_error_count()
        return round((errors / total) * 100.0, 2)

    def get_average_latency(self) -> float:
        """Calculate mean latency in milliseconds across all recorded events."""
        query = "SELECT AVG(latency_ms) FROM events"
        rows = self.duckdb_service.query(query)
        val = rows[0][0] if rows and rows[0][0] is not None else 0.0
        return round(float(val), 2)

    def get_overview(self) -> AnalyticsOverviewResponse:
        """
        Compute consolidated platform overview metrics in a single aggregated query.
        """
        query = """
        SELECT 
            COUNT(*) AS total_events,
            SUM(CASE WHEN status_code >= 400 OR event_type IN ('payment_failed', 'api_error', 'order_cancelled') THEN 1 ELSE 0 END) AS total_errors,
            AVG(latency_ms) AS avg_latency
        FROM events
        """
        rows = self.duckdb_service.query(query)
        if not rows or rows[0][0] == 0:
            return AnalyticsOverviewResponse(
                total_events=0,
                total_errors=0,
                error_rate=0.0,
                average_latency_ms=0.0,
            )

        total_events = int(rows[0][0])
        total_errors = int(rows[0][1] or 0)
        avg_latency = float(rows[0][2] or 0.0)

        error_rate = round((total_errors / total_events) * 100.0, 2) if total_events > 0 else 0.0

        return AnalyticsOverviewResponse(
            total_events=total_events,
            total_errors=total_errors,
            error_rate=error_rate,
            average_latency_ms=round(avg_latency, 2),
        )

    def get_service_metrics(self) -> List[ServiceMetricItem]:
        """
        Return aggregate metrics grouped by originating service.
        """
        query = """
        SELECT 
            service,
            COUNT(*) AS event_count,
            SUM(CASE WHEN status_code >= 400 OR event_type IN ('payment_failed', 'api_error', 'order_cancelled') THEN 1 ELSE 0 END) AS error_count,
            AVG(latency_ms) AS avg_latency
        FROM events
        GROUP BY service
        ORDER BY event_count DESC, service ASC
        """
        rows = self.duckdb_service.query(query)
        items: List[ServiceMetricItem] = []

        for row in rows:
            service = str(row[0])
            event_count = int(row[1])
            error_count = int(row[2] or 0)
            avg_latency = float(row[3] or 0.0)
            error_rate = round((error_count / event_count) * 100.0, 2) if event_count > 0 else 0.0

            items.append(
                ServiceMetricItem(
                    service=service,
                    event_count=event_count,
                    error_count=error_count,
                    error_rate=error_rate,
                    average_latency_ms=round(avg_latency, 2),
                )
            )

        return items

    def get_time_window_metrics(self, window_minutes: int = 1) -> List[TimeWindowMetricItem]:
        """
        Return aggregated metrics bucketed into time intervals (default 1-minute).
        """
        query = f"""
        SELECT 
            time_bucket(INTERVAL '{window_minutes} minute', timestamp) AS window_start,
            service,
            event_type,
            COUNT(*) AS event_count,
            SUM(CASE WHEN status_code >= 400 OR event_type IN ('payment_failed', 'api_error') THEN 1 ELSE 0 END) AS error_count,
            SUM(CASE WHEN status_code < 400 AND event_type NOT IN ('payment_failed', 'api_error') THEN 1 ELSE 0 END) AS success_count,
            AVG(latency_ms) AS avg_latency
        FROM events
        GROUP BY window_start, service, event_type
        ORDER BY window_start DESC, service, event_type
        """
        rows = self.duckdb_service.query(query)
        items: List[TimeWindowMetricItem] = []

        for row in rows:
            window_start = row[0]
            service = str(row[1])
            event_type = str(row[2])
            event_count = int(row[3])
            error_count = int(row[4] or 0)
            success_count = int(row[5] or 0)
            avg_latency = float(row[6] or 0.0)
            error_rate = round((error_count / event_count) * 100.0, 2) if event_count > 0 else 0.0

            items.append(
                TimeWindowMetricItem(
                    time_window=window_start,
                    service=service,
                    event_type=event_type,
                    event_count=event_count,
                    error_count=error_count,
                    success_count=success_count,
                    error_rate=error_rate,
                    average_latency_ms=round(avg_latency, 2),
                )
            )

        return items


def get_analytics_service(
    duckdb_service: DuckDBService = Depends(get_duckdb_service)
) -> AnalyticsService:
    """Dependency provider returning an AnalyticsService instance."""
    return AnalyticsService(duckdb_service=duckdb_service)
