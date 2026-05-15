"""Simple in-process metrics counters for logpipe."""
from __future__ import annotations

import threading
import time
from collections import defaultdict
from typing import Dict


class Metrics:
    """Thread-safe counters and gauges collected during pipeline execution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._counters: Dict[str, int] = defaultdict(int)
        self._gauges: Dict[str, float] = {}
        self._started_at: float = time.monotonic()

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    def increment(self, name: str, amount: int = 1) -> None:
        """Increment a counter by *amount* (default 1)."""
        with self._lock:
            self._counters[name] += amount

    def counter(self, name: str) -> int:
        """Return the current value of a counter (0 if never set)."""
        with self._lock:
            return self._counters[name]

    # ------------------------------------------------------------------
    # Gauges
    # ------------------------------------------------------------------

    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge to an absolute value."""
        with self._lock:
            self._gauges[name] = value

    def gauge(self, name: str) -> float:
        """Return the current gauge value (0.0 if never set)."""
        with self._lock:
            return self._gauges.get(name, 0.0)

    # ------------------------------------------------------------------
    # Snapshot
    # ------------------------------------------------------------------

    def snapshot(self) -> dict:
        """Return a copy of all metrics as a plain dict."""
        with self._lock:
            return {
                "uptime_seconds": round(time.monotonic() - self._started_at, 3),
                "counters": dict(self._counters),
                "gauges": dict(self._gauges),
            }

    def reset(self) -> None:
        """Clear all counters and gauges (useful in tests)."""
        with self._lock:
            self._counters.clear()
            self._gauges.clear()
            self._started_at = time.monotonic()


# Module-level default instance so components can share one object easily.
default_metrics = Metrics()
