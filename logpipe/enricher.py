"""Enricher — attaches static or dynamic metadata to every event."""
from __future__ import annotations

from typing import Any, Callable, Dict, Union

_Value = Union[Any, Callable[[Dict[str, Any]], Any]]


class Enricher:
    """Attach extra fields to events before they reach a sink.

    Fields can be static values or callables that receive the event and
    return a value at enrichment time.

    Example::

        enricher = (
            Enricher()
            .add("env", "production")
            .add("host", lambda e: socket.gethostname())
        )
        enriched = enricher.enrich(event)
    """

    def __init__(self) -> None:
        self._fields: Dict[str, _Value] = {}
        self._overwrite: bool = True

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def add(self, key: str, value: _Value) -> "Enricher":
        """Register a field.  *value* may be a plain object or a callable."""
        if not isinstance(key, str) or not key:
            raise ValueError("key must be a non-empty string")
        self._fields[key] = value
        return self

    def overwrite(self, enabled: bool = True) -> "Enricher":
        """Control whether existing event keys are overwritten (default: True)."""
        self._overwrite = bool(enabled)
        return self

    # ------------------------------------------------------------------
    # Runtime
    # ------------------------------------------------------------------

    def enrich(self, event: Dict[str, Any]) -> Dict[str, Any]:
        """Return a *new* dict that is *event* plus the registered fields."""
        out = dict(event)
        for key, value in self._fields.items():
            if not self._overwrite and key in out:
                continue
            out[key] = value(event) if callable(value) else value
        return out

    # ------------------------------------------------------------------
    # Dunder helpers
    # ------------------------------------------------------------------

    def __len__(self) -> int:  # number of registered fields
        return len(self._fields)

    def __repr__(self) -> str:
        return f"Enricher(fields={list(self._fields)!r}, overwrite={self._overwrite})"
