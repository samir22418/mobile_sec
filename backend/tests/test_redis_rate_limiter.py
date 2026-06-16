"""Tests for RedisRateLimiter and the make_rate_limiter factory.

All Redis-backed tests use fakeredis so no real Redis instance is required.
Concurrency correctness is verified by running 20 threads against a shared
FakeRedis instance with max_requests=10.
"""

from __future__ import annotations

import threading

import fakeredis

from app.services.rate_limiter import InMemoryRateLimiter, RedisRateLimiter, make_rate_limiter
from tests.conftest import sample_payload

# ---------------------------------------------------------------------------
# Test 1: InMemoryRateLimiter still works (regression guard)
# ---------------------------------------------------------------------------

def test_in_memory_allows_up_to_max():
    limiter = InMemoryRateLimiter(max_requests=3, window_seconds=60)
    assert limiter.allow("k1") is True
    assert limiter.allow("k1") is True
    assert limiter.allow("k1") is True
    assert limiter.allow("k1") is False  # 4th request over limit


# ---------------------------------------------------------------------------
# Test 2: RedisRateLimiter enforces max_requests
# ---------------------------------------------------------------------------

def test_redis_limiter_enforces_max():
    client = fakeredis.FakeRedis()
    limiter = RedisRateLimiter(client, max_requests=3, window_seconds=60)
    assert limiter.allow("k2") is True
    assert limiter.allow("k2") is True
    assert limiter.allow("k2") is True
    assert limiter.allow("k2") is False  # 4th blocked


# ---------------------------------------------------------------------------
# Test 3: Different keys are counted independently
# ---------------------------------------------------------------------------

def test_redis_limiter_keys_are_independent():
    client = fakeredis.FakeRedis()
    limiter = RedisRateLimiter(client, max_requests=2, window_seconds=60)
    limiter.allow("keyA")
    limiter.allow("keyA")
    assert limiter.allow("keyA") is False   # keyA exhausted
    assert limiter.allow("keyB") is True    # keyB unaffected


# ---------------------------------------------------------------------------
# Test 4: Unlimited when max_requests=0
# ---------------------------------------------------------------------------

def test_redis_limiter_unlimited_when_max_requests_zero():
    client = fakeredis.FakeRedis()
    limiter = RedisRateLimiter(client, max_requests=0, window_seconds=60)
    for _ in range(200):
        assert limiter.allow("any") is True


# ---------------------------------------------------------------------------
# Test 5: Concurrent requests — exactly max_requests are allowed
# ---------------------------------------------------------------------------

def test_redis_limiter_concurrency_correct_count():
    client = fakeredis.FakeRedis()
    MAX = 10
    N_THREADS = 20
    limiter = RedisRateLimiter(client, max_requests=MAX, window_seconds=60)

    results: list[bool] = []
    lock = threading.Lock()

    def make_request() -> None:
        result = limiter.allow("shared")
        with lock:
            results.append(result)

    threads = [threading.Thread(target=make_request) for _ in range(N_THREADS)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    allowed = sum(1 for r in results if r)
    blocked = sum(1 for r in results if not r)
    assert allowed == MAX, f"Expected {MAX} allowed, got {allowed}"
    assert blocked == N_THREADS - MAX, f"Expected {N_THREADS - MAX} blocked, got {blocked}"


# ---------------------------------------------------------------------------
# Test 6: make_rate_limiter returns InMemoryRateLimiter when no URL given
# ---------------------------------------------------------------------------

def test_make_rate_limiter_no_url_returns_in_memory():
    limiter = make_rate_limiter("", max_requests=5, window_seconds=60)
    assert isinstance(limiter, InMemoryRateLimiter)


# ---------------------------------------------------------------------------
# Test 7: make_rate_limiter returns InMemoryRateLimiter on unreachable Redis
# ---------------------------------------------------------------------------

def test_make_rate_limiter_unreachable_redis_falls_back():
    limiter = make_rate_limiter(
        "redis://127.0.0.1:19999/0",  # nothing listening here
        max_requests=5,
        window_seconds=60,
    )
    assert isinstance(limiter, InMemoryRateLimiter)


# ---------------------------------------------------------------------------
# Test 8: API returns 429 when Redis-backed limiter is exhausted
# ---------------------------------------------------------------------------

def test_api_telemetry_rate_limited_with_redis_backend(app, client):
    MAX = 2
    redis_client = fakeredis.FakeRedis()
    app.state.telemetry_rate_limiter = RedisRateLimiter(redis_client, max_requests=MAX, window_seconds=60)

    for i in range(MAX):
        resp = client.post(
            "/api/v1/telemetry",
            json=sample_payload(payload_id=f"rl-{i:03d}", scan_id=i + 1),
        )
        assert resp.status_code == 202, f"Request {i} should pass, got {resp.status_code}"

    # The (MAX+1)th request should be blocked regardless of payload_id
    resp = client.post(
        "/api/v1/telemetry",
        json=sample_payload(payload_id="rl-overflow", scan_id=MAX + 1),
    )
    assert resp.status_code == 429
    assert resp.json()["detail"]["error"] == "rate_limited"
