"""Rich health-check endpoint — DB, Redis, and Kafka reachability."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)

router = APIRouter()


def _check_db(request: Request) -> dict:
    try:
        session_factory = request.app.state.session_factory
        with session_factory() as session:
            session.execute(__import__("sqlalchemy").text("SELECT 1"))
        return {"status": "ok"}
    except Exception as exc:
        logger.warning("health/db check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _check_redis(request: Request) -> dict:
    settings = request.app.state.settings
    if not settings.redis_url:
        return {"status": "not_configured"}
    try:
        limiter = request.app.state.telemetry_rate_limiter
        # RedisRateLimiter exposes _client; InMemoryRateLimiter does not.
        redis_client = getattr(limiter, "_client", None)
        if redis_client is None:
            return {"status": "fallback_in_memory"}
        redis_client.ping()
        return {"status": "ok"}
    except Exception as exc:
        logger.warning("health/redis check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


def _check_kafka(request: Request) -> dict:
    settings = request.app.state.settings
    if settings.event_publisher != "kafka":
        return {"status": "not_configured"}
    producer = request.app.state.producer
    if producer is None:
        return {"status": "error", "detail": "producer not initialised"}
    try:
        # KafkaProducer.bootstrap_connected() performs a quick metadata fetch.
        connected = producer.bootstrap_connected()
        return {"status": "ok" if connected else "error", "connected": connected}
    except Exception as exc:
        logger.warning("health/kafka check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}


@router.get("/health")
def health(request: Request) -> JSONResponse:
    checks = {
        "db": _check_db(request),
        "redis": _check_redis(request),
        "kafka": _check_kafka(request),
    }
    degraded = any(v.get("status") == "error" for v in checks.values())
    status_code = 503 if degraded else 200
    return JSONResponse(
        status_code=status_code,
        content={
            "status": "degraded" if degraded else "ok",
            "service": "aegis-backend",
            "checks": checks,
        },
    )
