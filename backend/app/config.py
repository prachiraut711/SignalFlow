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
    
    # CORS Origins (comma-separated or list)
    CORS_ORIGINS: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    
    # Relational Database (PostgreSQL) - Placeholder for future phases
    DATABASE_URL: str = "postgresql://signalflow:signalflow_dev@localhost:5432/signalflow_db"
    
    # Message Broker / Stream Buffer (Redis) - Placeholder for future phases
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Columnar Analytical Store (DuckDB) - Placeholder for future phases
    DUCKDB_PATH: str = "signalflow_analytics.duckdb"
    
    # AI / LLM Integration (Gemini) - Placeholder for future phases
    GEMINI_API_KEY: str | None = None

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


@lru_cache()
def get_settings() -> Settings:
    """Return a cached instance of application settings."""
    return Settings()
