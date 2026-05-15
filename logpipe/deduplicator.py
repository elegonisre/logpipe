"""Event deduplication using a rolling hash window."""

from __future__ import annotations

import hashlib
import time
from collections import OrderedDict
from typing import Any, Dict, Optional


def _event_hash(event: Dict[str, Any]) -> str:
    """Return a stable SHA-1 hex digest for *event*."""
    # Sort keys so that insertion order does not affect the digest.
    normalised = "|".join(
        f"{k}={event[k]}" for k in sorted(event.keys())
    )
    return hashlib.sha1(normalised.encode()).hexdigest()


class Deduplicator:
    """Drop duplicate events seen within a sliding time window.

    Parameters
    ----------
    window_seconds:
        How long (in seconds) a seen event hash is remembered.  After
        this period the same event is treated as new again.
    max_size:
        Upper bound on the number of hashes kept in memory at once.
        Oldest entries are evicted first when the limit is reached.
    """

    def __init__(self, window_seconds: float = 60.0, max_size: int = 10_000) -> None:
        if window_seconds <= 0:
            raise ValueError("window_seconds must be positive")
        if max_size < 1:
            raise ValueError("max_size must be at least 1")
        self._window = window_seconds
        self._max_size = max_size
        # Maps hash -> timestamp of first occurrence in the current window.
        self._seen: OrderedDict[str, float] = OrderedDict()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_duplicate(self, event: Dict[str, Any]) -> bool:
        """Return *True* if *event* is a duplicate within the current window."""
        self._evict_expired()
        digest = _event_hash(event)
        if digest in self._seen:
            return True
        self._record(digest)
        return False

    def reset(self) -> None:
        """Clear all remembered hashes."""
        self._seen.clear()

    @property
    def size(self) -> int:
        """Number of hashes currently tracked."""
        return len(self._seen)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _record(self, digest: str) -> None:
        if len(self._seen) >= self._max_size:
            # Evict the oldest entry to stay within the size cap.
            self._seen.popitem(last=False)
        self._seen[digest] = time.monotonic()

    def _evict_expired(self) -> None:
        now = time.monotonic()
        cutoff = now - self._window
        # OrderedDict preserves insertion order; oldest entries are first.
        while self._seen:
            digest, ts = next(iter(self._seen.items()))
            if ts < cutoff:
                del self._seen[digest]
            else:
                break
