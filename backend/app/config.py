"""
Application Configuration Module

Loads environment variables via Pydantic BaseSettings.
All configuration is centralized here for easy maintenance and test overriding.
"""

from functools import lru_cache
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # Application Info
    PROJECT_NAME: str = "SignalFlow Backend"
    VERSION: str = "0.1.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    
    # Server Binding
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # CORS Origins
    FRONTEND_URL: str | None = None
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # Embedded Worker Execution (Render / single-service deployment)
    # When True, FastAPI starts the event worker in the same event loop
    EMBED_WORKER: bool = False

    # Relational Database (PostgreSQL / Neon)
    DATABASE_URL: str = "postgresql://signalflow:signalflow_dev@localhost:5432/signalflow_db"
    
    # Message Broker / Stream Buffer (Redis / Upstash)
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_STREAM_NAME: str = "signalflow:events"
    REDIS_CONSUMER_GROUP: str = "signalflow-processors"
    REDIS_CONSUMER_NAME: str = "worker-1"
    
    # Columnar Analytical Store (DuckDB)
    DUCKDB_PATH: str = "data/signalflow.duckdb"
    
    # OpenRouter AI Configuration (Phase 6)
    OPENROUTER_API_KEY: str = ""
    OPENROUTER_MODEL: str = "openrouter/free"
    OPENROUTER_BASE_URL: str = "https://openrouter.ai/api/v1"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()
