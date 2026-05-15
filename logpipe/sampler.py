"""Event sampler — forwards only a deterministic fraction of events."""
from __future__ import annotations

import hashlib
import math
from typing import Any, Dict, Optional

Event = Dict[str, Any]


class Sampler:
    """Keep every 1-in-N events, optionally keyed on a field value.

    Parameters
    ----------
    rate:
        Fraction of events to keep, expressed as a float in (0, 1].
        ``1.0`` means keep everything; ``0.1`` means keep ~10 %.
    key:
        Optional event field whose value is hashed to make the sampling
        decision deterministic for the same logical entity (e.g. ``"user_id"``).
        When *None* a simple modulo counter is used.
    """

    def __init__(self, rate: float, key: Optional[str] = None) -> None:
        if not (0 < rate <= 1.0):
            raise ValueError(f"rate must be in (0, 1], got {rate!r}")
        self._rate = rate
        self._key = key
        self._counter: int = 0
        # Pre-compute integer threshold for hash-based sampling (0..2^32-1).
        self._threshold: int = math.floor(rate * (2**32))

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def rate(self) -> float:
        return self._rate

    def should_keep(self, event: Event) -> bool:
        """Return *True* if *event* should be forwarded."""
        if self._key is not None:
            return self._hash_keep(event)
        return self._counter_keep()

    def reset(self) -> None:
        """Reset the internal counter (useful in tests)."""
        self._counter = 0

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _counter_keep(self) -> bool:
        keep = (self._counter % max(1, round(1 / self._rate))) == 0
        self._counter += 1
        return keep

    def _hash_keep(self, event: Event) -> bool:
        value = str(event.get(self._key, ""))
        digest = hashlib.md5(value.encode(), usedforsecurity=False).digest()
        # Take first 4 bytes as an unsigned 32-bit integer.
        num = int.from_bytes(digest[:4], "big")
        return num < self._threshold
