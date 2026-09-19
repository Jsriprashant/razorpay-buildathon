"""A minimal in-memory rate limiter for the public, unauthenticated apply
endpoint. No existing utility to reuse and no external store (e.g. Redis) is
part of this build, so this is a simple fixed-window counter per client IP.
It resets on process restart, which is acceptable for this demo build.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque

_WINDOW_SECONDS = 60.0
_MAX_REQUESTS = 5

_hits: dict[str, deque[float]] = defaultdict(deque)


def is_rate_limited(key: str, max_requests: int = _MAX_REQUESTS, window_seconds: float = _WINDOW_SECONDS) -> bool:
    now = time.monotonic()
    bucket = _hits[key]
    while bucket and now - bucket[0] > window_seconds:
        bucket.popleft()
    if len(bucket) >= max_requests:
        return True
    bucket.append(now)
    return False
