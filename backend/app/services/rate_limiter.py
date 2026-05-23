from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Deque


class InMemoryRateLimiter:
    """Small local rate limiter for the MVP API process.

    This is intentionally process-local. It protects local/dev deployments from
    accidental floods without pretending to be a production distributed limiter.
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
