from __future__ import annotations

import json
import logging

from kafka import KafkaConsumer, KafkaProducer

from app.config import Settings

logger = logging.getLogger(__name__)

# Header keys used for retry tracking
HEADER_RETRY_COUNT = b"retry-count"
HEADER_LAST_ERROR = b"last-error"

MAX_RETRIES = 3


def get_producer(settings: Settings) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        acks="all",
        retries=5,
        compression_type="gzip",
        request_timeout_ms=30_000,
        max_block_ms=10_000,
    )


def get_consumer(settings: Settings, topic: str, group_id: str) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
        session_timeout_ms=30_000,
        heartbeat_interval_ms=10_000,
        max_poll_interval_ms=300_000,
    )


def publish_to_dlq(
    producer: KafkaProducer,
    topic: str,
    payload_id: str,
    error: str,
    retry_count: int,
) -> None:
    """Publish a failed message to the dead-letter topic for manual review."""
    dlq_topic = f"{topic}.dlq"
    dlq_record = {
        "payload_id": payload_id,
        "error": error[:500],
        "retry_count": retry_count,
    }
    producer.send(dlq_topic, dlq_record)
    producer.flush()
    logger.warning("Published payload_id=%s to DLQ topic=%s after %d retries", payload_id, dlq_topic, retry_count)


def kafka_health_check(bootstrap_servers: str, timeout_ms: int = 5_000) -> bool:
    """Return True if Kafka brokers are reachable."""
    from kafka.admin import KafkaAdminClient
    try:
        admin = KafkaAdminClient(
            bootstrap_servers=bootstrap_servers.split(","),
            request_timeout_ms=timeout_ms,
        )
        admin.close()
        return True
    except Exception:
        return False
