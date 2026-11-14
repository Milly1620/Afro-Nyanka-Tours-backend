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

    def __init__(
        self,
        max_failures: int = 5,
        window_seconds: int = 15 * 60,
        detail: str = "Too many failed login attempts. Try again later.",
    ):
        self.max_failures = max_failures
        self.window_seconds = window_seconds
        self.detail = detail
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
                    detail=self.detail,
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

    def allow(self, key: str) -> bool:
        """Record an attempt and report whether it is within the limit (no exception)."""
        try:
            self.begin([key])
        except HTTPException:
            return False
        return True

    def reset(self, key: str) -> None:
        with self._lock:
            self._failures.pop(key, None)

    def reset_all(self) -> None:
        with self._lock:
            self._failures.clear()


class KnownLoginIps:
    """IPs each admin has logged in from successfully (in-process, lost on restart).

    Lets the real admin through the per-email cap while an attacker on other
    IPs is tripping it. The per email+IP limit still applies to these IPs.
    """

    MAX_PER_EMAIL = 20

    def __init__(self):
        self._ips: dict[str, deque] = {}
        self._lock = threading.Lock()

    def add(self, email: str, ip: str) -> None:
        with self._lock:
            ips = self._ips.setdefault(email, deque(maxlen=self.MAX_PER_EMAIL))
            if ip in ips:
                ips.remove(ip)
            ips.append(ip)

    def contains(self, email: str, ip: str) -> bool:
        with self._lock:
            return ip in self._ips.get(email, ())

    def reset_all(self) -> None:
        with self._lock:
            self._ips.clear()


# Per email+IP: the normal brute-force guard.
login_rate_limiter = LoginRateLimiter(max_failures=5)
# Per email across all IPs: caps guessing even if IPs rotate.
email_rate_limiter = LoginRateLimiter(max_failures=20)
known_login_ips = KnownLoginIps()

# Forgot-password: per IP (429) and per email (silently skipped, so the reply never differs).
_FORGOT_DETAIL = "Too many password reset requests. Try again later."
forgot_ip_limiter = LoginRateLimiter(max_failures=10, window_seconds=60 * 60, detail=_FORGOT_DETAIL)
forgot_email_limiter = LoginRateLimiter(max_failures=3, window_seconds=60 * 60, detail=_FORGOT_DETAIL)
