"""Event transformer: apply a sequence of mutations to a log event dict."""
from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

Event = Dict[str, Any]
TransformFn = Callable[[Event], Optional[Event]]


class Transformer:
    """Applies an ordered list of transform functions to events.

    Each transform receives the current event dict and must return either a
    (possibly mutated) dict or ``None`` to drop the event entirely.
    """

    def __init__(self) -> None:
        self._steps: List[TransformFn] = []

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def add(self, fn: TransformFn) -> "Transformer":
        """Append a transform step; returns *self* for chaining."""
        if not callable(fn):
            raise TypeError("transform step must be callable")
        self._steps.append(fn)
        return self

    def rename(self, old_key: str, new_key: str) -> "Transformer":
        """Rename *old_key* to *new_key* if present."""
        def _rename(event: Event) -> Optional[Event]:
            if old_key in event:
                event[new_key] = event.pop(old_key)
            return event
        return self.add(_rename)

    def drop_field(self, key: str) -> "Transformer":
        """Remove *key* from the event if it exists."""
        def _drop(event: Event) -> Optional[Event]:
            event.pop(key, None)
            return event
        return self.add(_drop)

    def add_field(self, key: str, value: Any) -> "Transformer":
        """Set *key* to a static *value* (overwrites existing)."""
        def _add(event: Event) -> Optional[Event]:
            event[key] = value
            return event
        return self.add(_add)

    def mask_field(self, key: str, mask: str = "***") -> "Transformer":
        """Replace the value of *key* with *mask* if present."""
        def _mask(event: Event) -> Optional[Event]:
            if key in event:
                event[key] = mask
            return event
        return self.add(_mask)

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def apply(self, event: Event) -> Optional[Event]:
        """Run all steps in order; returns the final event or ``None``."""
        current: Optional[Event] = dict(event)  # work on a shallow copy
        for step in self._steps:
            if current is None:
                return None
            current = step(current)
        return current

    def __len__(self) -> int:  # pragma: no cover
        return len(self._steps)
