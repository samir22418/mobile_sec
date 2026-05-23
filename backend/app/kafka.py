import json
from typing import Any

from kafka import KafkaProducer, KafkaConsumer

from app.config import Settings

def get_producer(settings: Settings) -> KafkaProducer:
    return KafkaProducer(
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        value_serializer=lambda v: json.dumps(v).encode("utf-8"),
        retries=3,
    )

def get_consumer(settings: Settings, topic: str, group_id: str) -> KafkaConsumer:
    return KafkaConsumer(
        topic,
        bootstrap_servers=settings.kafka_bootstrap_servers.split(","),
        group_id=group_id,
        auto_offset_reset="earliest",
        enable_auto_commit=False,
        value_deserializer=lambda v: json.loads(v.decode("utf-8")),
    )
