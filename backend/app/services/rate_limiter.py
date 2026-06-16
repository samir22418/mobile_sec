"""Rate-limiting implementations.

Two backends are provided:
  - InMemoryRateLimiter  — process-local deque, for local/dev use (no external deps)
  - RedisRateLimiter     — sliding-window sorted-set in Redis, shared across replicas

Use make_rate_limiter() to get the right one based on settings.
"""

from __future__ import annotations

import logging
import time
import uuid
from collections import defaultdict, deque
from typing import Deque

logger = logging.getLogger(__name__)


class InMemoryRateLimiter:
    """Process-local sliding-window rate limiter (dev/fallback).

    Warning: stale buckets accumulate until the process is restarted. Use
    RedisRateLimiter for production deployments with multiple replicas.
    """

    def __init__(self, max_requests: int = 120, window_seconds: int = 60) -> None:
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        self._buckets: dict[str, Deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        if self.max_requests <= 0 or self.window_seconds <= 0:
            return True

        now = time.time()
        window_start = now - self.window_seconds
        bucket = self._buckets[key]
        while bucket and bucket[0] <= window_start:
            bucket.popleft()

        if len(bucket) >= self.max_requests:
            return False

        bucket.append(now)
        return True


class RedisRateLimiter:
    """Sliding-window rate limiter backed by a Redis sorted set.

    Each call to allow() atomically adds the current timestamp as a sorted-set
    member, removes entries outside the window, counts remaining members, and
    sets a TTL so idle keys are automatically evicted (fixing the memory-leak
    present in InMemoryRateLimiter).

    The MULTI/EXEC pipeline ensures the ZADD→ZREMRANGEBYSCORE→ZCARD sequence is
    atomic, so concurrent requests across multiple API replicas are counted
    correctly.
    """

    def __init__(
        self,
        client,
        max_requests: int,
        window_seconds: int,
    ) -> None:
        self._client = client
        self.max_requests = max_requests
        self.window_seconds = window_seconds

    def allow(self, key: str) -> bool:
        if self.max_requests <= 0 or self.window_seconds <= 0:
            return True

        now_ms = int(time.time() * 1000)
        window_start_ms = now_ms - (self.window_seconds * 1000)
        # Unique member prevents score collisions for sub-millisecond bursts
        member = f"{now_ms}:{uuid.uuid4().hex}"
        rkey = f"aegis:rl:{key}"

        pipe = self._client.pipeline(transaction=True)
        pipe.zadd(rkey, {member: now_ms})
        pipe.zremrangebyscore(rkey, 0, window_start_ms)
        pipe.zcard(rkey)
        pipe.expire(rkey, self.window_seconds * 2)
        results = pipe.execute()

        count = results[2]  # ZCARD result (includes the member just added)
        return count <= self.max_requests


def make_rate_limiter(
    redis_url: str,
    max_requests: int,
    window_seconds: int,
) -> InMemoryRateLimiter | RedisRateLimiter:
    """Return a RedisRateLimiter when redis_url is set and Redis is reachable.

    Falls back to InMemoryRateLimiter on missing URL or connection failure so
    local development works without a Redis instance.
    """
    if redis_url:
        try:
            import redis as redis_lib

            client = redis_lib.from_url(
                redis_url,
                decode_responses=False,
                socket_connect_timeout=2,
            )
            client.ping()
            logger.info("Rate limiter: using Redis at %s", redis_url)
            return RedisRateLimiter(client, max_requests, window_seconds)
        except Exception as exc:
            logger.warning(
                "Redis unavailable (%s) — falling back to in-memory rate limiter", exc
            )

    return InMemoryRateLimiter(max_requests, window_seconds)
