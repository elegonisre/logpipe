"""Simple token-bucket rate limiter for controlling event throughput."""

import time
from threading import Lock


class RateLimiter:
    """Token-bucket rate limiter.

    Allows up to *rate* events per *period* seconds.  Thread-safe.

    Parameters
    ----------
    rate:   maximum number of events allowed per period.
    period: length of the replenishment window in seconds (default 1.0).
    """

    def __init__(self, rate: float, period: float = 1.0) -> None:
        if rate <= 0:
            raise ValueError("rate must be positive")
        if period <= 0:
            raise ValueError("period must be positive")

        self._rate = rate
        self._period = period
        self._tokens: float = rate
        self._last_refill: float = time.monotonic()
        self._lock = Lock()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def allow(self) -> bool:
        """Return True and consume one token if the event is allowed."""
        with self._lock:
            self._refill()
            if self._tokens >= 1.0:
                self._tokens -= 1.0
                return True
            return False

    def reset(self) -> None:
        """Refill the bucket to its maximum capacity immediately."""
        with self._lock:
            self._tokens = self._rate
            self._last_refill = time.monotonic()

    @property
    def tokens(self) -> float:
        """Current token count (snapshot; may change immediately after read)."""
        with self._lock:
            self._refill()
            return self._tokens

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refill(self) -> None:
        now = time.monotonic()
        elapsed = now - self._last_refill
        new_tokens = elapsed * (self._rate / self._period)
        if new_tokens > 0:
            self._tokens = min(self._rate, self._tokens + new_tokens)
            self._last_refill = now
