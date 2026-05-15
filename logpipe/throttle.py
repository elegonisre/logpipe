"""Event throttler: suppress repeated identical events within a time window."""
from __future__ import annotations

import time
from typing import Any, Dict, Optional


class Throttle:
    """Suppress duplicate events that occur within *window* seconds.

    Unlike :class:`~logpipe.deduplicator.Deduplicator`, Throttle is keyed on a
    single field (e.g. ``"message"`` or ``"error_code"``), making it cheap for
    high-throughput pipelines where only one field determines identity.

    Parameters
    ----------
    key:
        The event field used to identify an event's "topic".
    window:
        Minimum number of seconds that must elapse before the same topic is
        allowed through again.  Must be > 0.
    """

    def __init__(self, key: str, window: float = 60.0) -> None:
        if not key or not isinstance(key, str):
            raise ValueError("key must be a non-empty string")
        if window <= 0:
            raise ValueError("window must be greater than zero")
        self._key = key
        self._window = window
        self._last_seen: Dict[Any, float] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def key(self) -> str:
        return self._key

    @property
    def window(self) -> float:
        return self._window

    def allow(self, event: Dict[str, Any], *, _now: Optional[float] = None) -> bool:
        """Return ``True`` if the event should be forwarded, ``False`` if throttled."""
        topic = event.get(self._key)
        if topic is None:
            # Events without the key field are always forwarded.
            return True
        now = _now if _now is not None else time.monotonic()
        last = self._last_seen.get(topic)
        if last is None or (now - last) >= self._window:
            self._last_seen[topic] = now
            return True
        return False

    def reset(self, topic: Optional[Any] = None) -> None:
        """Clear throttle state.  Pass *topic* to clear only that entry."""
        if topic is None:
            self._last_seen.clear()
        else:
            self._last_seen.pop(topic, None)

    def tracked(self) -> int:
        """Return the number of topics currently being tracked."""
        return len(self._last_seen)
