import threading
import time
from collections import defaultdict, deque

from fastapi import HTTPException, status


class LoginRateLimiter:
    """In-process failed-login limiter: `max_failures` within `window_seconds` blocks the key."""

    def __init__(self, max_failures: int = 5, window_seconds: int = 15 * 60):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def _prune(self, key: str, now: float) -> deque:
        failures = self._failures[key]
        while failures and now - failures[0] > self.window_seconds:
            failures.popleft()
        return failures

    def check(self, key: str) -> None:
        with self._lock:
            if len(self._prune(key, time.monotonic())) >= self.max_failures:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed login attempts. Try again later.",
                )

    def fail(self, key: str) -> None:
        with self._lock:
            now = time.monotonic()
            self._prune(key, now).append(now)

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._failures.clear()


login_rate_limiter = LoginRateLimiter()
