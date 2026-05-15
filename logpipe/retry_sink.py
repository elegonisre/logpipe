"""RetrySink — wraps another sink and retries failed writes with backoff."""
from __future__ import annotations

import time
import logging
from typing import Any

from logpipe.sink import BaseSink

log = logging.getLogger(__name__)

_SENTINEL = object()


class RetrySink(BaseSink):
    """Wraps *inner* and retries ``write`` on exception.

    Parameters
    ----------
    inner:      The real sink to forward events to.
    max_retries: Maximum number of retry attempts (not counting the first try).
    backoff:    Base sleep time in seconds between attempts; doubles each retry.
    """

    def __init__(
        self,
        inner: BaseSink,
        *,
        max_retries: int = 3,
        backoff: float = 0.1,
    ) -> None:
        if max_retries < 0:
            raise ValueError("max_retries must be >= 0")
        if backoff < 0:
            raise ValueError("backoff must be >= 0")
        self._inner = inner
        self._max_retries = max_retries
        self._backoff = backoff
        self._attempts: int = 0
        self._failures: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def attempts(self) -> int:
        """Total write attempts made (including retries)."""
        return self._attempts

    @property
    def failures(self) -> int:
        """Events that ultimately could not be written after all retries."""
        return self._failures

    def write(self, event: dict[str, Any]) -> None:
        delay = self._backoff
        last_exc: Exception | None = None
        for attempt in range(self._max_retries + 1):
            self._attempts += 1
            try:
                self._inner.write(event)
                return
            except Exception as exc:  # noqa: BLE001
                last_exc = exc
                if attempt < self._max_retries:
                    log.warning(
                        "RetrySink: write failed (attempt %d/%d): %s — retrying in %.3fs",
                        attempt + 1,
                        self._max_retries + 1,
                        exc,
                        delay,
                    )
                    time.sleep(delay)
                    delay *= 2
        self._failures += 1
        log.error("RetrySink: giving up after %d attempts: %s", self._max_retries + 1, last_exc)

    def flush(self) -> None:
        self._inner.flush()
