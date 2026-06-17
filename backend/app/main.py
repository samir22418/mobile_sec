from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router
from app.config import Settings, load_settings
from app.database import init_db, make_session_factory
from app.logging_config import configure_logging
from app.services.auth import AuthService
from app.services.ingestion import IngestionService
from app.services.play_integrity import PlayIntegrityService
from app.services.rate_limiter import make_rate_limiter
from app.services.raw_store import RawPayloadStore
from app.services.validation import TelemetryValidationService

logger = logging.getLogger(__name__)


def create_app(settings: Settings | None = None) -> FastAPI:
    configure_logging()
    settings = settings or load_settings()
    app = FastAPI(title="AEGIS Backend", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=list(settings.cors_allowed_origins),
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    session_factory = make_session_factory(settings.database_url)
    init_db(session_factory)

    raw_store = RawPayloadStore(settings.raw_payload_dir)
    play_integrity = PlayIntegrityService(
        settings.google_play_integrity_api_key,
        settings.google_play_integrity_package_name,
    )
    producer = None
    if (
        not settings.process_inline
        and settings.event_publisher == "kafka"
        and settings.kafka_bootstrap_servers
    ):
        try:
            from app.kafka import get_producer

            producer = get_producer(settings)
        except Exception as error:
            logger.warning("Failed to connect to Kafka: %s. Running without Kafka producer.", error)

    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.raw_store = raw_store
    app.state.producer = producer
    app.state.play_integrity = play_integrity
    app.state.telemetry_validator = TelemetryValidationService(settings.telemetry_schema_path)
    app.state.auth_service = AuthService(settings.accepted_enrollment_tokens, settings.analyst_tokens)
    app.state.telemetry_rate_limiter = make_rate_limiter(
        settings.redis_url,
        max_requests=settings.telemetry_rate_limit_max_requests,
        window_seconds=settings.telemetry_rate_limit_window_seconds,
    )
    app.state.auth_rate_limiter = make_rate_limiter(
        settings.redis_url,
        max_requests=20,
        window_seconds=60,
    )
    app.state.ingestion_service = IngestionService(
        raw_store=raw_store,
        session_factory=session_factory,
        producer=producer,
        topic=settings.kafka_telemetry_topic,
        process_inline=settings.process_inline,
        play_integrity_service=play_integrity,
        settings=settings,
    )

    app.include_router(router)
    return app


app = create_app()
