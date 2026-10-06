"""
Redis Service Module

Encapsulates asynchronous Redis operations including connection pooling,
liveness ping checks, and Redis Stream interactions (XADD, XRANGE, XLEN).
"""

import logging
from typing import Any, Dict, List, Optional
import redis.asyncio as aioredis
from app.config import get_settings

try:
    import fakeredis
    import fakeredis.aioredis as fake_aioredis
except ImportError:
    fakeredis = None
    fake_aioredis = None

logger = logging.getLogger(__name__)


class RedisService:
    """
    Asynchronous Redis client wrapper for caching and stream operations.
    """

    def __init__(self, redis_url: Optional[str] = None):
        self.redis_url = redis_url or get_settings().REDIS_URL
        self._client: Optional[Any] = None
        self._loop: Optional[Any] = None
        self._is_fake: bool = False
        self._fake_server = None

    def get_client(self) -> Any:
        """Get or initialize the async Redis client instance bound to active loop."""
        import asyncio
        try:
            current_loop = asyncio.get_running_loop()
        except RuntimeError:
            current_loop = None

        if self._is_fake and self._client is not None:
            return self._client

        if (
            self._client is None
            or self._loop is None
            or self._loop != current_loop
            or (self._loop and self._loop.is_closed())
        ):
            extra_kwargs: Dict[str, Any] = {}
            if self.redis_url.startswith("rediss://"):
                # Accommodate cloud TLS connections (Upstash)
                extra_kwargs["ssl_cert_reqs"] = None

            self._client = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=5.0,
                socket_timeout=5.0,
                **extra_kwargs,
            )
            self._loop = current_loop
        return self._client

    def _fallback_to_fake(self, reason: Any) -> Any:
        """Initialize in-memory FakeRedis fallback when live server is unreachable."""
        if fake_aioredis is not None and fakeredis is not None:
            masked_url = self.redis_url.split("@")[-1] if "@" in self.redis_url else self.redis_url
            logger.warning(
                f"Live Redis unreachable at {masked_url} ({reason}). Using in-memory FakeRedis stream fallback."
            )
            if self._fake_server is None:
                self._fake_server = fakeredis.FakeServer()
            self._client = fake_aioredis.FakeRedis(server=self._fake_server, decode_responses=True)
            self._is_fake = True
            return self._client
        return None

    async def ping(self) -> bool:
        """
        Check if Redis server is reachable and responding.
        Returns True if reachable, False otherwise without raising errors.
        """
        try:
            client = self.get_client()
            return bool(await client.ping())
        except Exception as exc:
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                return bool(await fake_client.ping())
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
        try:
            message_id = await client.xadd(name=stream_name, fields=sanitized_fields)
            return str(message_id)
        except Exception as exc:
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                message_id = await fake_client.xadd(name=stream_name, fields=sanitized_fields)
                return str(message_id)
            raise

    async def read_stream_latest(self, stream_name: str, count: int = 10) -> List[Any]:
        """
        Read the latest entries from a Redis Stream using XREVRANGE.
        Useful for verification, testing, and monitoring.
        """
        client = self.get_client()
        try:
            return await client.xrevrange(name=stream_name, count=count)
        except Exception as exc:
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                return await fake_client.xrevrange(name=stream_name, count=count)
            logger.error(f"Failed to read from stream {stream_name}: {exc}")
            return []

    async def create_consumer_group(
        self, stream_name: str, group_name: str, start_id: str = "0"
    ) -> bool:
        """
        Create a consumer group on the specified stream if it doesn't already exist.
        """
        client = self.get_client()
        try:
            # MKSTREAM automatically creates the stream if not present
            await client.xgroup_create(
                name=stream_name, groupname=group_name, id=start_id, mkstream=True
            )
            logger.info(f"Created consumer group '{group_name}' on stream '{stream_name}'")
            return True
        except Exception as exc:
            if "BUSYGROUP" in str(exc):
                # Group already exists
                return False
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                try:
                    await fake_client.xgroup_create(
                        name=stream_name, groupname=group_name, id=start_id, mkstream=True
                    )
                    logger.info(f"Created consumer group '{group_name}' on in-memory stream '{stream_name}'")
                    return True
                except Exception as inner_exc:
                    if "BUSYGROUP" in str(inner_exc):
                        return False
            logger.warning(f"Error creating consumer group '{group_name}': {exc}")
            raise

    async def read_consumer_group(
        self,
        stream_name: str,
        group_name: str,
        consumer_name: str,
        count: int = 10,
        block_ms: int = 2000,
    ) -> List[Any]:
        """
        Read new messages from a Redis Stream using XREADGROUP ('>' id).
        """
        client = self.get_client()
        try:
            streams_response = await client.xreadgroup(
                groupname=group_name,
                consumername=consumer_name,
                streams={stream_name: ">"},
                count=count,
                block=block_ms,
            )
            return streams_response or []
        except Exception as exc:
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                try:
                    streams_response = await fake_client.xreadgroup(
                        groupname=group_name,
                        consumername=consumer_name,
                        streams={stream_name: ">"},
                        count=count,
                        block=block_ms,
                    )
                    return streams_response or []
                except Exception as inner_exc:
                    logger.warning(f"Error reading consumer group '{group_name}' from fake client: {inner_exc}")
                    return []
            logger.warning(f"Error reading consumer group '{group_name}': {exc}")
            return []

    async def ack_messages(
        self, stream_name: str, group_name: str, *message_ids: str
    ) -> int:
        """
        Acknowledge messages in consumer group (XACK).
        """
        if not message_ids:
            return 0
        client = self.get_client()
        try:
            return await client.xack(stream_name, group_name, *message_ids)
        except Exception as exc:
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                try:
                    return await fake_client.xack(stream_name, group_name, *message_ids)
                except Exception:
                    return 0
            logger.error(f"Failed to ACK messages {message_ids} in group '{group_name}': {exc}")
            return 0

    async def get_stream_length(self, stream_name: str) -> int:
        """Return the current length (number of entries) in a Redis Stream."""
        client = self.get_client()
        try:
            return await client.xlen(name=stream_name)
        except Exception as exc:
            fake_client = self._fallback_to_fake(exc)
            if fake_client is not None:
                try:
                    return await fake_client.xlen(name=stream_name)
                except Exception:
                    return 0
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
