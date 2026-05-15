"""Event buffer that accumulates events and flushes them in batches."""

from __future__ import annotations

import time
from typing import Callable, List, Optional


class Buffer:
    """Accumulate events and flush when size or age threshold is reached.

    Args:
        max_size: Maximum number of events before an automatic flush.
        max_age: Maximum seconds to hold events before an automatic flush.
        on_flush: Callable invoked with the list of events on each flush.
    """

    def __init__(
        self,
        max_size: int = 100,
        max_age: float = 5.0,
        on_flush: Optional[Callable[[List[dict]], None]] = None,
    ) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if max_age <= 0:
            raise ValueError("max_age must be > 0")

        self._max_size = max_size
        self._max_age = max_age
        self._on_flush = on_flush
        self._events: List[dict] = []
        self._opened_at: float = time.monotonic()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def add(self, event: dict) -> bool:
        """Add an event to the buffer.  Returns True if a flush was triggered."""
        self._events.append(event)
        if self._should_flush():
            self.flush()
            return True
        return False

    def flush(self) -> List[dict]:
        """Flush all buffered events and reset the buffer.

        Returns the list of events that were flushed.
        """
        events = self._events
        self._events = []
        self._opened_at = time.monotonic()
        if events and self._on_flush is not None:
            self._on_flush(events)
        return events

    def pending(self) -> int:
        """Return the number of events currently in the buffer."""
        return len(self._events)

    def age(self) -> float:
        """Return seconds since the buffer was last flushed (or created)."""
        return time.monotonic() - self._opened_at

    def is_expired(self) -> bool:
        """Return True if the buffer has been open longer than *max_age*."""
        return self.age() >= self._max_age

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _should_flush(self) -> bool:
        return len(self._events) >= self._max_size or self.is_expired()
