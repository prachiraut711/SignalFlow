"""
Database and Storage Infrastructure Package

1. PostgreSQL (Relational metadata, rules, audit logs via SQLAlchemy)
2. Redis (Event streams & pub/sub caching)
3. DuckDB (In-process OLAP analytical queries)
"""

from typing import Any, AsyncGenerator
from app.db.duckdb import DuckDBService, get_duckdb_service

__all__ = [
    "get_db_session",
    "get_redis_client",
    "get_duckdb_connection",
    "DuckDBService",
    "get_duckdb_service",
]


async def get_db_session() -> AsyncGenerator[Any, None]:
    """
    Placeholder generator for SQLAlchemy async database sessions.
    Will be configured with asyncpg in Phase 4+.
    """
    yield None


async def get_redis_client() -> Any:
    """
    Return active async Redis client from RedisService.
    """
    from app.services.redis_service import get_redis_service
    return get_redis_service().get_client()


def get_duckdb_connection() -> Any:
    """
    Return active DuckDB connection context from DuckDBService.
    """
    return get_duckdb_service().get_connection()
