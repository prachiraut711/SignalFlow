"""
SQLAlchemy Signal & Association Models for Incident Correlation

Represents aggregated business incidents (Signals) derived from one or more
metric anomalies across services and regions within dynamic time windows.
"""

from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import (
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from app.models.anomaly import Base, AnomalyRecord


class SignalRecord(Base):
    """
    Persistent record representing an operational incident signal.
    Correlates multiple raw metric anomalies into a unified business incident.
    """
    __tablename__ = "signals"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_key = Column(String(150), nullable=False, unique=True, index=True)
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(20), nullable=False, index=True)  # 'INFO', 'WARNING', 'HIGH', 'CRITICAL'
    service = Column(String(100), nullable=False, index=True)
    region = Column(String(100), nullable=False, index=True)
    status = Column(String(20), nullable=False, default="OPEN", index=True)  # 'OPEN', 'RESOLVED'
    first_detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    last_detected_at = Column(DateTime(timezone=True), nullable=False, index=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False
    )
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False
    )

    signal_anomalies = relationship(
        "SignalAnomaly",
        back_populates="signal",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SignalAnomaly.id.asc()",
    )

    @property
    def anomalies(self) -> List[AnomalyRecord]:
        """Convenience property extracting linked AnomalyRecord entities."""
        return [sa.anomaly for sa in self.signal_anomalies if sa.anomaly is not None]

    @property
    def related_anomalies_count(self) -> int:
        """Count of anomalies attached to this signal."""
        return len(self.signal_anomalies) if self.signal_anomalies else 0


class SignalAnomaly(Base):
    """
    Association table linking individual AnomalyRecord instances to a SignalRecord.
    Enforces uniqueness so the same anomaly cannot be linked to the same signal twice.
    """
    __tablename__ = "signal_anomalies"

    id = Column(Integer, primary_key=True, autoincrement=True)
    signal_id = Column(
        Integer,
        ForeignKey("signals.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )
    anomaly_id = Column(
        Integer,
        ForeignKey("anomalies.id", ondelete="CASCADE"),
        nullable=False,
        index=True
    )

    signal = relationship("SignalRecord", back_populates="signal_anomalies")
    anomaly = relationship("AnomalyRecord", lazy="joined")

    __table_args__ = (
        UniqueConstraint("signal_id", "anomaly_id", name="uq_signal_anomaly"),
    )
