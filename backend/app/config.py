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
    accepted_enrollment_tokens: tuple[str, ...] = ("sample-token",)
    process_inline: bool = True
    worker_poll_interval_seconds: float = 5.0


def load_settings() -> Settings:
    tokens = os.getenv("AEGIS_ACCEPTED_ENROLLMENT_TOKENS", "sample-token")
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
        accepted_enrollment_tokens=tuple(token.strip() for token in tokens.split(",") if token.strip()),
        process_inline=os.getenv("AEGIS_PROCESS_INLINE", "true").lower() in {"1", "true", "yes", "on"},
        worker_poll_interval_seconds=float(os.getenv("AEGIS_WORKER_POLL_INTERVAL_SECONDS", "5")),
    )
