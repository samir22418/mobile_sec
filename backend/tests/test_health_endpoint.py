"""Tests for the rich /health endpoint.

Verifies that the endpoint checks DB, Redis, and Kafka reachability and returns
appropriate status codes (200 ok / 503 degraded).
"""
from __future__ import annotations




def test_health_ok(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "ok"
    assert "checks" in body
    assert "db" in body["checks"]
    assert "redis" in body["checks"]
    assert "kafka" in body["checks"]


def test_health_db_check_is_ok(client):
    resp = client.get("/health")
    assert resp.json()["checks"]["db"]["status"] == "ok"


def test_health_redis_not_configured_when_no_url(client):
    """Default test settings have no redis_url → redis check shows not_configured."""
    resp = client.get("/health")
    assert resp.json()["checks"]["redis"]["status"] == "not_configured"


def test_health_kafka_not_configured_when_inline(client):
    """Default test settings have event_publisher != 'kafka' → kafka check shows not_configured."""
    resp = client.get("/health")
    assert resp.json()["checks"]["kafka"]["status"] == "not_configured"


def test_health_db_error_returns_503(client, app):
    """If the DB is unreachable the endpoint returns HTTP 503 with status=degraded."""
    import sqlalchemy

    original_factory = app.state.session_factory

    class _FailSession:
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def execute(self, *args, **kwargs):
            raise sqlalchemy.exc.OperationalError("DB gone", None, None)

    class _FailFactory:
        def __call__(self):
            return _FailSession()

    app.state.session_factory = _FailFactory()
    try:
        resp = client.get("/health")
        assert resp.status_code == 503
        body = resp.json()
        assert body["status"] == "degraded"
        assert body["checks"]["db"]["status"] == "error"
    finally:
        app.state.session_factory = original_factory


def test_health_redis_ok_when_limiter_has_client(client, app):
    """When a RedisRateLimiter is wired, redis check calls ping() and reports ok."""
    import fakeredis
    from app.services.rate_limiter import RedisRateLimiter

    real_limiter = app.state.telemetry_rate_limiter
    fake_client = fakeredis.FakeRedis()
    app.state.telemetry_rate_limiter = RedisRateLimiter(fake_client, max_requests=100, window_seconds=60)
    # Override settings to expose redis_url non-empty so the check runs
    from app.config import Settings
    app.state.settings = Settings(
        redis_url="redis://fake:6379/0",
        telemetry_schema_path=app.state.settings.telemetry_schema_path,
        accepted_enrollment_tokens=app.state.settings.accepted_enrollment_tokens,
        analyst_tokens=app.state.settings.analyst_tokens,
    )
    try:
        resp = client.get("/health")
        assert resp.json()["checks"]["redis"]["status"] == "ok"
    finally:
        app.state.telemetry_rate_limiter = real_limiter
        app.state.settings = Settings(
            database_url=str(app.state.settings.database_url),
            telemetry_schema_path=app.state.settings.telemetry_schema_path,
            accepted_enrollment_tokens=app.state.settings.accepted_enrollment_tokens,
            analyst_tokens=app.state.settings.analyst_tokens,
        )


def test_health_includes_service_name(client):
    resp = client.get("/health")
    assert resp.json()["service"] == "aegis-backend"
