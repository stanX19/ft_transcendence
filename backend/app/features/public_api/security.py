"""Authentication and process-local throttling for the public API."""

from __future__ import annotations

import secrets
import threading
import time
from collections import defaultdict, deque
from typing import Deque

from fastapi import Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader

from app.core.config import get_settings


api_key_header = APIKeyHeader(
    name="X-API-Key",
    auto_error=False,
    description="The integration key configured for the LibraryOS public API.",
)


class PublicApiRateLimiter:
    """A small fixed-window limiter suitable for the single API worker."""

    _window_seconds = 60.0

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._requests: dict[str, Deque[float]] = defaultdict(deque)
        self._limits: dict[str, int] = {}

    def allow(self, key: str, limit: int, *, now: float | None = None) -> bool:
        current_time = time.monotonic() if now is None else now
        with self._lock:
            # A changed setting represents a fresh deterministic test/config
            # boundary and should not inherit the previous window's count.
            if self._limits.get(key) != limit:
                self._requests[key].clear()
                self._limits[key] = limit

            requests = self._requests[key]
            cutoff = current_time - self._window_seconds
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= limit:
                return False
            requests.append(current_time)
            return True

    def reset(self) -> None:
        """Clear in-memory state; useful for isolated application tests."""

        with self._lock:
            self._requests.clear()
            self._limits.clear()


public_api_rate_limiter = PublicApiRateLimiter()


def require_public_api_key(
    api_key: str | None = Security(api_key_header),
) -> str:
    """Require the configured integration key without consulting browser auth."""

    configured_key = get_settings().public_api_key
    if not api_key or not configured_key or not secrets.compare_digest(
        api_key,
        configured_key,
    ):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED)
    return api_key


def enforce_public_api_rate_limit(
    api_key: str = Depends(require_public_api_key),
) -> str:
    """Count only authenticated public-API requests and reject excess traffic."""

    limit = get_settings().public_api_rate_limit_per_minute
    if not public_api_rate_limiter.allow(api_key, limit):
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS)
    return api_key
