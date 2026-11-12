import threading
import time
from collections import deque
from typing import Iterable

from fastapi import HTTPException, status


class LoginRateLimiter:
    """In-process limiter on login attempts.

    `begin` checks and records an attempt in one step under the lock, so a
    burst of parallel requests can't all slip past the check before any of
    them is counted. A successful login takes its attempt back via `succeed`.
    """

    def __init__(self, max_failures: int = 5, window_seconds: int = 15 * 60):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self._failures: dict[str, deque] = {}
        self._lock = threading.Lock()

    def _prune_all(self, now: float) -> None:
        for key in list(self._failures):
            attempts = self._failures[key]
            while attempts and now - attempts[0] > self.window_seconds:
                attempts.popleft()
            if not attempts:
                del self._failures[key]

    def begin(self, keys: Iterable[str]) -> None:
        keys = list(keys)
        with self._lock:
            now = time.monotonic()
            self._prune_all(now)
            if any(len(self._failures.get(k, ())) >= self.max_failures for k in keys):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Too many failed login attempts. Try again later.",
                )
            for key in keys:
                self._failures.setdefault(key, deque()).append(now)

    def succeed(self, keys: Iterable[str]) -> None:
        with self._lock:
            for key in keys:
                attempts = self._failures.get(key)
                if attempts:
                    attempts.pop()
                    if not attempts:
                        del self._failures[key]

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._failures.clear()


# Per email+IP: the normal brute-force guard.
login_rate_limiter = LoginRateLimiter(max_failures=5)
# Per email across all IPs: caps guessing even if IPs rotate.
email_rate_limiter = LoginRateLimiter(max_failures=20)
