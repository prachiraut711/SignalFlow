"""
SQLAlchemy Anomaly Record Model for PostgreSQL
"""

from datetime import datetime, timezone
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class AnomalyRecord(Base):
    """
    Persistent record representing a detected statistical or ML anomaly.
    Stored in PostgreSQL for platform-level audit, alerting, and incident correlation.
    """
    __tablename__ = "anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    detected_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
        index=True
    )
    time_window = Column(DateTime(timezone=True), nullable=False, index=True)
    service = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, default="global")
    metric = Column(String(50), nullable=False)  # e.g., 'error_rate', 'latency_ms', 'event_count'
    anomaly_type = Column(String(50), nullable=False)  # e.g., 'error_rate_spike', 'latency_spike'
    current_value = Column(Float, nullable=False)
    baseline_value = Column(Float, nullable=False)
    percentage_change = Column(Float, nullable=False)
    z_score = Column(Float, nullable=True)
    isolation_score = Column(Float, nullable=True)
    severity = Column(String(20), nullable=False, index=True)  # 'INFO', 'WARNING', 'HIGH', 'CRITICAL'
    reason = Column(Text, nullable=False)

    __table_args__ = (
        UniqueConstraint("service", "time_window", "metric", name="uq_service_window_metric"),
    )
