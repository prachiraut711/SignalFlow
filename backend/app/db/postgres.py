"""
PostgreSQL Relational Storage Management Module

Provides SQLAlchemy engine, session maker, table initialization, and session
lifecycles for platform-level anomaly and audit records.
"""

from contextlib import contextmanager
import logging
import os
from typing import Generator, Optional
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from app.config import get_settings
from app.models.anomaly import Base

logger = logging.getLogger(__name__)

_engine = None
_session_factory = None


def get_engine():
    """Get or create singleton SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        db_url = settings.DATABASE_URL

        # Use sync driver for SQLAlchemy synchronous session management
        # (psycopg2 or sqlite for tests)
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")

        if "sqlite" in db_url:
            _engine = create_engine(db_url, connect_args={"check_same_thread": False})
        else:
            try:
                temp_engine = create_engine(
                    db_url,
                    pool_pre_ping=True,
                    pool_size=5,
                    max_overflow=10,
                    connect_args={"connect_timeout": 2}
                )
                with temp_engine.connect() as conn:
                    pass
                _engine = temp_engine
                logger.info(f"Connected to PostgreSQL database at {db_url}")
            except Exception as exc:
                fallback_path = os.path.abspath(os.path.join(os.getcwd(), "data", "signalflow_platform.db"))
                os.makedirs(os.path.dirname(fallback_path), exist_ok=True)
                logger.warning(
                    f"PostgreSQL unreachable at {db_url} ({exc}). Using local store 'sqlite:///{fallback_path}'"
                )
                _engine = create_engine(f"sqlite:///{fallback_path}", connect_args={"check_same_thread": False})
    return _engine


def get_session_factory():
    """Get or create singleton sessionmaker."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=get_engine(),
        )
    return _session_factory


def init_db(engine=None) -> bool:
    """
    Initialize all relational database tables.
    Returns True if successful, False if database is unreachable.
    """
    eng = engine or get_engine()
    try:
        Base.metadata.create_all(bind=eng)
        logger.info("Initialized PostgreSQL relational database schema (anomalies table ready)")
        return True
    except Exception as exc:
        logger.warning(
            f"Relational database at {eng.url} is not currently reachable: {exc}."
        )
        return False


@contextmanager
def get_db_session() -> Generator[Session, None, None]:
    """
    Context manager yielding a transactional database session.
    Commits automatically on exit or rolls back on exception.
    """
    session: Session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency yielding a database session."""
    session: Session = get_session_factory()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
