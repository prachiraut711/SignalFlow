"""
DuckDB Analytics Storage Module

Provides connection management, schema initialization, and transactional
execution for the SignalFlow embedded analytical event store.
"""

from contextlib import contextmanager
import logging
import os
from pathlib import Path
import time
from typing import Any, Dict, Generator, List, Optional, Tuple
import duckdb

from app.config import get_settings

logger = logging.getLogger(__name__)

CREATE_EVENTS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS events (
    event_id VARCHAR PRIMARY KEY,
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL,
    service VARCHAR NOT NULL,
    event_type VARCHAR NOT NULL,
    region VARCHAR NOT NULL,
    status_code INTEGER NOT NULL,
    latency_ms DOUBLE NOT NULL,
    value DOUBLE DEFAULT 0.0,
    user_id VARCHAR,
    ingested_at TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_events_service ON events(service);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type);
"""


class DuckDBService:
    """
    Service wrapper around DuckDB embedded database.
    Manages short-lived connections to accommodate multi-process concurrency
    between background stream workers and API query workers.
    """

    def __init__(self, db_path: Optional[str] = None):
        settings = get_settings()
        raw_path = db_path or settings.DUCKDB_PATH

        if raw_path == ":memory:":
            self.db_path = ":memory:"
            self._mem_conn: Optional[duckdb.DuckDBPyConnection] = duckdb.connect(":memory:")
        else:
            self._mem_conn = None
            # Resolve relative paths consistently relative to project or backend
            p = Path(raw_path)
            if not p.is_absolute():
                # If path starts with 'data', put it in project root data/
                p = Path(os.getcwd()) / p
            self.db_path = str(p.resolve())
            # Ensure target directory exists
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)

        self._initialize_schema()

    @contextmanager
    def get_connection(
        self,
        read_only: bool = False,
        max_retries: int = 15,
        retry_delay: float = 0.05
    ) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """
        Context manager returning an active DuckDB connection with automatic retry
        handling for transient file locks in multi-process environments.
        """
        if self.db_path == ":memory:" and self._mem_conn is not None:
            yield self._mem_conn
            return

        conn = None
        last_error = None

        for attempt in range(max_retries):
            try:
                conn = duckdb.connect(self.db_path, read_only=read_only)
                break
            except Exception as exc:
                last_error = exc
                time.sleep(retry_delay * (1.2 ** attempt))

        if conn is None:
            logger.error(f"Failed to connect to DuckDB at {self.db_path}: {last_error}")
            raise last_error

        try:
            yield conn
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def _initialize_schema(self) -> None:
        """Create analytical event tables and indices if not already present."""
        with self.get_connection(read_only=False) as conn:
            conn.execute(CREATE_EVENTS_TABLE_SQL)
        logger.info(f"Initialized DuckDB analytics schema at {self.db_path}")

    def insert_event(self, event_record: Dict[str, Any]) -> None:
        """Insert a single processed event record into DuckDB."""
        self.insert_events_batch([event_record])

    def insert_events_batch(self, event_records: List[Dict[str, Any]]) -> int:
        """
        Batch insert multiple normalized event records.
        Uses INSERT OR IGNORE to guarantee idempotency on duplicate event IDs.
        """
        if not event_records:
            return 0

        rows = [
            (
                rec["event_id"],
                rec["timestamp"],
                rec["service"],
                rec["event_type"],
                rec.get("region", "global"),
                int(rec["status_code"]),
                float(rec["latency_ms"]),
                float(rec.get("value") or 0.0),
                rec.get("user_id"),
                rec["ingested_at"],
            )
            for rec in event_records
        ]

        insert_sql = """
        INSERT OR IGNORE INTO events (
            event_id, timestamp, service, event_type, region,
            status_code, latency_ms, value, user_id, ingested_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """

        with self.get_connection(read_only=False) as conn:
            conn.executemany(insert_sql, rows)

        return len(rows)

    def query(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Tuple[Any, ...]]:
        """Execute a read query and return all rows as tuples."""
        with self.get_connection(read_only=True) as conn:
            cursor = conn.execute(sql, params or ())
            return cursor.fetchall()

    def query_dicts(self, sql: str, params: Optional[Tuple[Any, ...]] = None) -> List[Dict[str, Any]]:
        """Execute a read query and return all rows as dictionaries."""
        with self.get_connection(read_only=True) as conn:
            cursor = conn.execute(sql, params or ())
            columns = [col[0] for col in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]


# Global singleton instance
_duckdb_service_instance: Optional[DuckDBService] = None


def get_duckdb_service(db_path: Optional[str] = None) -> DuckDBService:
    """Dependency provider returning singleton DuckDBService instance."""
    global _duckdb_service_instance
    if _duckdb_service_instance is None or db_path is not None:
        _duckdb_service_instance = DuckDBService(db_path=db_path)
    return _duckdb_service_instance
