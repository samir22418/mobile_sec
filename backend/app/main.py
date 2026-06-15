from __future__ import annotations

from fastapi import FastAPI

from app.api.routes import router
from app.config import Settings, load_settings
from app.database import init_db, make_session_factory
from app.services.auth import AuthService
from app.services.ingestion import IngestionService
from app.services.raw_store import RawPayloadStore
from app.services.validation import TelemetryValidationService


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or load_settings()
    app = FastAPI(title="AEGIS Backend", version="0.1.0")

    session_factory = make_session_factory(settings.database_url)
    init_db(session_factory)

    raw_store = RawPayloadStore(settings.raw_payload_dir)
    app.state.settings = settings
    app.state.session_factory = session_factory
    app.state.raw_store = raw_store
    app.state.telemetry_validator = TelemetryValidationService(settings.telemetry_schema_path)
    app.state.auth_service = AuthService(settings.accepted_enrollment_tokens)
    app.state.ingestion_service = IngestionService(
        raw_store=raw_store,
        session_factory=session_factory,
        process_inline=settings.process_inline,
    )

    app.include_router(router)
    return app


app = create_app()

