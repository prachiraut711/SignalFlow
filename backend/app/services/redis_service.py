"""
Redis Service Module

Encapsulates asynchronous Redis operations including connection pooling,
liveness ping checks, and Redis Stream interactions (XADD, XRANGE, XLEN).
"""

import logging
from typing import Any, Dict, List, Optional
import redis.asyncio as aioredis
from app.config import get_settings

logger = logging.getLogger(__name__)


class RedisService:
    """
    Asynchronous Redis client wrapper for caching and stream operations.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or get_settings().REDIS_URL
        self._client: Optional[aioredis.Redis] = None
        self._loop: Optional[Any] = None

    def get_client(self) -> aioredis.Redis:
        """Get or initialize the async Redis client instance bound to active loop."""
        import asyncio
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if (
            self._client is None
            or self._loop is None
            or self._loop != current_loop
            or (self._loop and self._loop.is_closed())
        ):
            self._client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=3.0,
            )
            self._loop = current_loop
        return self._client

    async def ping(self) -> bool:
        """
        Check if Redis server is reachable and responding.
        Returns True if reachable, False otherwise without raising errors.
        """
        try:
            client = self.get_client()
            return await client.ping()
        except Exception as exc:
            logger.warning(f"Redis ping failed: {exc}")
            return False

    async def add_to_stream(self, stream_name: str, fields: Dict[str, Any]) -> str:
        """
        Append an event or data payload to the specified Redis Stream (XADD).

        Args:
            stream_name: Name/key of the stream (e.g. 'signalflow:events')
            fields: Dictionary of field name to string/primitive values

        Returns:
            Redis generated message ID (e.g. '1728148200000-0')
        """
        client = self.get_client()
        # Redis XADD requires string, bytes, or numeric values
        sanitized_fields = {
            k: (v if isinstance(v, (str, int, float, bytes)) else str(v))
            for k, v in fields.items()
        }
        message_id = await client.xadd(name=stream_name, fields=sanitized_fields)
        return str(message_id)

    async def read_stream_latest(self, stream_name: str, count: int = 10) -> List[Any]:
        """
        Read the latest entries from a Redis Stream using XREVRANGE.
        Useful for verification, testing, and monitoring.
        """
        client = self.get_client()
        try:
            return await client.xrevrange(name=stream_name, count=count)
        except Exception as exc:
            logger.error(f"Failed to read from stream {stream_name}: {exc}")
            return []

    async def get_stream_length(self, stream_name: str) -> int:
        """Return the current length (number of entries) in a Redis Stream."""
        client = self.get_client()
        try:
            return await client.xlen(name=stream_name)
        except Exception:
            return 0

    async def close(self) -> None:
        """Close connection pool cleanly."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None


# Global singleton instance
_redis_service_instance: Optional[RedisService] = None


def get_redis_service() -> RedisService:
    """Dependency provider returning singleton RedisService instance."""
    global _redis_service_instance
    if _redis_service_instance is None:
        _redis_service_instance = RedisService()
    return _redis_service_instance
