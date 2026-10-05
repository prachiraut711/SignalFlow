"""
Redis Stream Background Event Processing Worker

Continuously consumes events from Redis Stream consumer groups,
normalizes telemetry records, stores them into DuckDB, and ACKs processed messages.
"""

import asyncio
from datetime import datetime
import json
import logging
import signal
import sys
from typing import Any, Dict, List, Optional, Tuple

from app.config import get_settings
from app.db.duckdb import DuckDBService, get_duckdb_service
from app.services.redis_service import RedisService, get_redis_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("SignalFlowWorker")


class EventWorker:
    """
    Background worker consuming from Redis Streams and persisting into DuckDB.
    """

    def __init__(
        self,
        redis_service: Optional[RedisService] = None,
        duckdb_service: Optional[DuckDBService] = None,
        stream_name: Optional[str] = None,
        group_name: Optional[str] = None,
        consumer_name: Optional[str] = None,
        batch_size: int = 50,
        block_ms: int = 2000,
    ):
        settings = get_settings()
        self.stream_name = stream_name or settings.REDIS_STREAM_NAME
        self.group_name = group_name or settings.REDIS_CONSUMER_GROUP
        self.consumer_name = consumer_name or settings.REDIS_CONSUMER_NAME
        self.batch_size = batch_size
        self.block_ms = block_ms

        self.redis_service = redis_service or get_redis_service()
        self.duckdb_service = duckdb_service or get_duckdb_service()
        self.is_running = False

    async def initialize_consumer_group(self) -> None:
        """Ensure stream and consumer group exist in Redis."""
        while True:
            try:
                await self.redis_service.create_consumer_group(
                    stream_name=self.stream_name,
                    group_name=self.group_name,
                    start_id="0",
                )
                logger.info(
                    f"Consumer group '{self.group_name}' ready on stream '{self.stream_name}'"
                )
                break
            except Exception as exc:
                if not self.is_running:
                    logger.warning(
                        f"Could not create consumer group '{self.group_name}': {exc}"
                    )
                    break
                logger.warning(
                    f"Waiting for Redis connection to create consumer group: {exc}. Retrying in 2s..."
                )
                await asyncio.sleep(2.0)

    def parse_message_payload(
        self, msg_id: str, fields: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:
        """
        Parse raw Redis Stream entry into a normalized dictionary for DuckDB.
        Returns None if parsing fails, logging the anomaly clearly.
        """
        try:
            # Check for serialized payload string
            raw_payload = fields.get("payload")
            if raw_payload:
                if isinstance(raw_payload, bytes):
                    raw_payload = raw_payload.decode("utf-8")
                data = json.loads(raw_payload)
            else:
                # Fallback to direct fields
                data = fields.copy()

            # Ensure required analytical fields
            event_id = data.get("event_id") or fields.get("event_id") or f"gen_{msg_id}"
            service = data.get("service") or fields.get("service")
            event_type = data.get("event_type") or fields.get("event_type")

            if not service or not event_type:
                logger.error(
                    f"Message {msg_id} discarded: missing required service or event_type: {fields}"
                )
                return None

            # Normalization
            normalized = {
                "event_id": str(event_id),
                "timestamp": data.get("timestamp") or datetime.utcnow().isoformat(),
                "service": str(service),
                "event_type": str(event_type),
                "region": str(data.get("region") or fields.get("region") or "global"),
                "status_code": int(data.get("status_code", 200)),
                "latency_ms": float(data.get("latency_ms", 0.0)),
                "value": float(data.get("value") or 0.0),
                "user_id": str(data["user_id"]) if data.get("user_id") else None,
                "ingested_at": data.get("ingested_at") or datetime.utcnow().isoformat(),
            }
            return normalized

        except (json.JSONDecodeError, ValueError, TypeError) as err:
            logger.error(f"Malformed stream entry {msg_id}: {err}. Fields: {fields}")
            return None

    async def process_batch(self) -> int:
        """
        Fetch a batch of messages from consumer group, store in DuckDB, and ACK.
        Returns count of successfully processed events.
        """
        streams_data = await self.redis_service.read_consumer_group(
            stream_name=self.stream_name,
            group_name=self.group_name,
            consumer_name=self.consumer_name,
            count=self.batch_size,
            block_ms=self.block_ms,
        )

        if not streams_data:
            return 0

        parsed_events: List[Dict[str, Any]] = []
        msg_ids_to_ack: List[str] = []

        for stream, messages in streams_data:
            for msg_id, fields in messages:
                msg_ids_to_ack.append(msg_id)
                event_record = self.parse_message_payload(msg_id, fields)
                if event_record:
                    parsed_events.append(event_record)

        if parsed_events:
            try:
                inserted_count = self.duckdb_service.insert_events_batch(parsed_events)
                logger.info(
                    f"Inserted {inserted_count} events into DuckDB (Stream: {self.stream_name})"
                )
            except Exception as exc:
                logger.error(f"Failed to batch insert events into DuckDB: {exc}")
                # Do not acknowledge in Redis so message can be retried
                return 0

        # Acknowledge processed / discarded messages in Redis
        if msg_ids_to_ack:
            await self.redis_service.ack_messages(
                self.stream_name, self.group_name, *msg_ids_to_ack
            )

        return len(parsed_events)

    async def run(self, stop_event: Optional[asyncio.Event] = None) -> None:
        """
        Continuous worker execution loop with resilient error recovery.
        """
        self.is_running = True
        logger.info(
            f"Starting SignalFlow EventWorker [{self.consumer_name}] "
            f"listening on '{self.stream_name}' in group '{self.group_name}'..."
        )

        await self.initialize_consumer_group()

        backoff = 1.0
        while self.is_running:
            if stop_event and stop_event.is_set():
                break

            try:
                processed = await self.process_batch()
                backoff = 1.0  # Reset backoff on success
                if processed == 0:
                    # Brief pause if queue was empty
                    await asyncio.sleep(0.1)

            except Exception as exc:
                logger.warning(
                    f"Transient worker processing error: {exc}. Backing off for {backoff:.1f}s..."
                )
                await asyncio.sleep(backoff)
                backoff = min(backoff * 1.5, 10.0)

        logger.info("EventWorker loop terminated gracefully.")

    def stop(self) -> None:
        """Signal worker to stop processing."""
        self.is_running = False


def main():
    """CLI Entrypoint for running the worker as a standalone daemon."""
    worker = EventWorker()
    stop_event = asyncio.Event()

    def handle_signal(sig, frame):
        logger.info(f"Received shutdown signal ({sig}). Stopping worker...")
        worker.stop()
        stop_event.set()

    # Register OS signals
    if sys.platform != "win32":
        signal.signal(signal.SIGINT, handle_signal)
        signal.signal(signal.SIGTERM, handle_signal)

    try:
        asyncio.run(worker.run(stop_event))
    except (KeyboardInterrupt, SystemExit):
        logger.info("Worker interrupted by user. Exiting.")


if __name__ == "__main__":
    main()
