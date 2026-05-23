from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]


@dataclass(frozen=True)
class Settings:
    database_url: str = f"sqlite:///{(REPO_DIR / 'backend-data' / 'aegis.db').as_posix()}"
    raw_payload_dir: Path = REPO_DIR / "backend-data" / "raw-payloads"
    telemetry_schema_path: Path = BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json"
    accepted_enrollment_tokens: tuple[str, ...] = tuple()
    analyst_tokens: tuple[str, ...] = tuple()
    process_inline: bool = True
    worker_poll_interval_seconds: float = 5.0
    event_publisher: str = "none"
    kafka_bootstrap_servers: str = "localhost:9092"
    kafka_telemetry_topic: str = "telemetry_events"


def load_settings() -> Settings:
    enrollment_tokens = os.getenv("AEGIS_ACCEPTED_ENROLLMENT_TOKENS", "")
    analyst_tokens = os.getenv("AEGIS_ANALYST_TOKENS", "")
    return Settings(
        database_url=os.getenv(
            "AEGIS_BACKEND_DATABASE_URL",
            f"sqlite:///{(REPO_DIR / 'backend-data' / 'aegis.db').as_posix()}",
        ),
        raw_payload_dir=Path(
            os.getenv("AEGIS_RAW_PAYLOAD_DIR", str(REPO_DIR / "backend-data" / "raw-payloads"))
        ),
        telemetry_schema_path=Path(
            os.getenv(
                "AEGIS_TELEMETRY_SCHEMA_PATH",
                str(BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json"),
            )
        ),
        accepted_enrollment_tokens=tuple(token.strip() for token in enrollment_tokens.split(",") if token.strip()),
        analyst_tokens=tuple(token.strip() for token in analyst_tokens.split(",") if token.strip()),
        process_inline=os.getenv("AEGIS_PROCESS_INLINE", "true").lower() in {"1", "true", "yes", "on"},
        worker_poll_interval_seconds=float(os.getenv("AEGIS_WORKER_POLL_INTERVAL_SECONDS", "5")),
        event_publisher=os.getenv("AEGIS_EVENT_PUBLISHER", "none").lower(),
        kafka_bootstrap_servers=os.getenv("AEGIS_KAFKA_BOOTSTRAP_SERVERS", "localhost:9092"),
        kafka_telemetry_topic=os.getenv("AEGIS_KAFKA_TELEMETRY_TOPIC", "telemetry_events"),
    )
