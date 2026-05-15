"""Redactor — masks sensitive field values before events reach a sink."""

from __future__ import annotations

import re
from typing import Callable, Dict, Iterable, Pattern, Union

_MaskFn = Callable[[str], str]

_BUILTIN_MASKS: Dict[str, _MaskFn] = {
    "full": lambda v: "***",
    "partial": lambda v: v[:2] + "***" if len(v) > 2 else "***",
    "hash": lambda v: "#" + str(abs(hash(v)) % 10 ** 8).zfill(8),
}


class Redactor:
    """Redact (mask) sensitive fields in log events.

    Usage::

        r = (
            Redactor()
            .add("password")
            .add("token", mask="partial")
            .add_pattern(r"secret_.*")
        )
        clean = r.redact(event)
    """

    def __init__(self) -> None:
        self._fields: Dict[str, _MaskFn] = {}
        self._patterns: list[tuple[Pattern[str], _MaskFn]] = []

    # ------------------------------------------------------------------
    # Builder API
    # ------------------------------------------------------------------

    def add(self, field: str, mask: Union[str, _MaskFn] = "full") -> "Redactor":
        """Register an exact field name to redact."""
        self._fields[field] = self._resolve_mask(mask)
        return self

    def add_pattern(
        self, pattern: str, mask: Union[str, _MaskFn] = "full"
    ) -> "Redactor":
        """Register a regex pattern; matching field names will be redacted."""
        self._patterns.append((re.compile(pattern), self._resolve_mask(mask)))
        return self

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def redact(self, event: dict) -> dict:
        """Return a new event with sensitive fields masked."""
        out = dict(event)
        for key, value in event.items():
            fn = self._mask_fn_for(key)
            if fn is not None and isinstance(value, str):
                out[key] = fn(value)
        return out

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _mask_fn_for(self, field: str) -> _MaskFn | None:
        if field in self._fields:
            return self._fields[field]
        for pattern, fn in self._patterns:
            if pattern.fullmatch(field):
                return fn
        return None

    @staticmethod
    def _resolve_mask(mask: Union[str, _MaskFn]) -> _MaskFn:
        if callable(mask):
            return mask
        if mask not in _BUILTIN_MASKS:
            raise ValueError(
                f"Unknown mask {mask!r}. Choose from {list(_BUILTIN_MASKS)} or pass a callable."
            )
        return _BUILTIN_MASKS[mask]
