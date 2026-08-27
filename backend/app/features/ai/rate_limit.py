"""Process-local per-user rate limiting for assistant requests."""

from __future__ import annotations

from collections import defaultdict, deque
import time
from threading import Lock

from fastapi import Depends, HTTPException, status

from app.core.config import get_settings
from app.core.dependencies import get_current_user


class AIRateLimiter:
    """A small fixed-window limiter for the project's single API worker."""

    def __init__(self, *, clock=time.monotonic) -> None:
        self._clock = clock
        self._requests: dict[int, deque[float]] = defaultdict(deque)
        self._lock = Lock()

    def allow(self, user_id: int, limit: int, *, now: float | None = None) -> bool:
        """Consume one request when the user is below the configured limit."""

        bounded_limit = max(1, int(limit))
        current = self._clock() if now is None else now
        cutoff = current - 60.0
        with self._lock:
            requests = self._requests[user_id]
            while requests and requests[0] <= cutoff:
                requests.popleft()
            if len(requests) >= bounded_limit:
                return False
            requests.append(current)
            return True

    def reset(self) -> None:
        """Clear state for isolated tests and local development."""

        with self._lock:
            self._requests.clear()


ai_rate_limiter = AIRateLimiter()


def enforce_ai_rate_limit(current_user=Depends(get_current_user)):
    """Return the authenticated user when its request is within the limit."""

    if not ai_rate_limiter.allow(
        current_user.id,
        get_settings().ai_rate_limit_per_minute,
    ):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="AI request limit exceeded.",
        )
    return current_user


__all__ = ["AIRateLimiter", "ai_rate_limiter", "enforce_ai_rate_limit"]
