from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


REPO_DIR = Path(__file__).resolve().parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[1]

# Tokens that are publicly known and must never be used outside local dev.
_KNOWN_WEAK_TOKENS: frozenset[str] = frozenset({"sample-token", "dev-token", "test-token"})


@dataclass(frozen=True)
class Settings:
    database_url: str = f"sqlite:///{(REPO_DIR / 'backend-data' / 'aegis.db').as_posix()}"
    raw_payload_dir: Path = REPO_DIR / "backend-data" / "raw-payloads"
    telemetry_schema_path: Path = BACKEND_DIR / "app" / "schemas" / "telemetry_schema_v1.json"
    # Empty by default — load_settings() fills this; fail closed outside dev.
    accepted_enrollment_tokens: tuple[str, ...] = ()
    # Separate key for analyst/console read endpoints (not the device enrollment token).
    # None means "no key required" — only acceptable when AEGIS_ENV=dev.
    console_api_key: str | None = None
    # False by default: ingest returns 202 immediately; a worker processes async.
    # Set AEGIS_PROCESS_INLINE=true only for local development / tests.
    process_inline: bool = False
    worker_poll_interval_seconds: float = 5.0


def load_settings() -> Settings:
    env = os.getenv("AEGIS_ENV", "production").lower()
    is_dev = env == "dev"

    raw_tokens = os.getenv("AEGIS_ACCEPTED_ENROLLMENT_TOKENS", "")
    tokens = tuple(t.strip() for t in raw_tokens.split(",") if t.strip())

    console_api_key: str | None = os.getenv("AEGIS_CONSOLE_API_KEY") or None

    if is_dev:
        # Supply safe defaults and continue — never block a developer's local run.
        if not tokens:
            tokens = ("sample-token",)
        if console_api_key is None:
            console_api_key = "dev-console-key"
    else:
        # Production / staging: fail fast rather than silently accepting weak config.
        if not tokens:
            raise ValueError(
                "AEGIS_ACCEPTED_ENROLLMENT_TOKENS must be set in non-dev environments. "
                "Set AEGIS_ENV=dev to use development defaults locally."
            )
        weak = set(tokens) & _KNOWN_WEAK_TOKENS
        if weak:
            raise ValueError(
                f"Enrollment token(s) {sorted(weak)} are known-weak defaults. "
                "Use a cryptographically strong secret in non-dev environments."
            )
        if console_api_key is None:
            raise ValueError(
                "AEGIS_CONSOLE_API_KEY must be set in non-dev environments. "
                "Set AEGIS_ENV=dev to skip this requirement locally."
            )

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
        accepted_enrollment_tokens=tokens,
        console_api_key=console_api_key,
        process_inline=os.getenv("AEGIS_PROCESS_INLINE", "false").lower() in {"1", "true", "yes", "on"},
        worker_poll_interval_seconds=float(os.getenv("AEGIS_WORKER_POLL_INTERVAL_SECONDS", "5")),
    )
