from __future__ import annotations

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta
from threading import Lock


class TokenValidationRateLimiter:
    def __init__(
        self,
        *,
        max_failures: int = 10,
        window_seconds: int = 900,
    ) -> None:
        self.max_failures = max_failures
        self.window = timedelta(seconds=window_seconds)
        self._failures: dict[str, deque[datetime]] = defaultdict(deque)
        self._lock = Lock()

    def check(self, client_key: str) -> None:
        with self._lock:
            now = datetime.now(UTC)
            bucket = self._failures[client_key]
            while bucket and now - bucket[0] > self.window:
                bucket.popleft()
            if len(bucket) >= self.max_failures:
                raise ValueError("Demasiados intentos fallidos. Intenta mas tarde.")

    def record_failure(self, client_key: str) -> None:
        with self._lock:
            self._failures[client_key].append(datetime.now(UTC))

    def reset(self, client_key: str) -> None:
        with self._lock:
            self._failures.pop(client_key, None)


_limiter: TokenValidationRateLimiter | None = None


def get_token_validation_rate_limiter() -> TokenValidationRateLimiter:
    global _limiter
    if _limiter is None:
        _limiter = TokenValidationRateLimiter()
    return _limiter
