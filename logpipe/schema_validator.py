"""Schema validation for parsed log events."""
from __future__ import annotations

from typing import Any, Callable, Dict, Iterable, Optional


class SchemaValidationError(Exception):
    """Raised when an event fails schema validation."""


class SchemaValidator:
    """Validates that events conform to a declared schema.

    A schema is a mapping of field names to type constraints or callable
    predicates.  Fields can be marked required or optional.

    Example usage::

        v = (
            SchemaValidator()
            .require("level", str)
            .require("ts", (int, float))
            .optional("host", str)
        )
        ok, errors = v.validate({"level": "info", "ts": 1234567890})
    """

    def __init__(self) -> None:
        self._required: Dict[str, Optional[Callable[[Any], bool]]] = {}
        self._optional: Dict[str, Optional[Callable[[Any], bool]]] = {}

    # ------------------------------------------------------------------
    # Builder helpers
    # ------------------------------------------------------------------

    def require(self, field: str, check: Any = None) -> "SchemaValidator":
        """Mark *field* as required, optionally with a type or predicate."""
        self._required[field] = self._normalise(check)
        return self

    def optional(self, field: str, check: Any = None) -> "SchemaValidator":
        """Mark *field* as optional but validated when present."""
        self._optional[field] = self._normalise(check)
        return self

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate(self, event: Dict[str, Any]) -> tuple[bool, list[str]]:
        """Return ``(is_valid, errors)`` for *event*."""
        errors: list[str] = []

        for field, check in self._required.items():
            if field not in event:
                errors.append(f"missing required field '{field}'")
            elif check is not None and not check(event[field]):
                errors.append(
                    f"field '{field}' failed validation (got {event[field]!r})"
                )

        for field, check in self._optional.items():
            if field in event and check is not None and not check(event[field]):
                errors.append(
                    f"field '{field}' failed validation (got {event[field]!r})"
                )

        return (len(errors) == 0, errors)

    def is_valid(self, event: Dict[str, Any]) -> bool:
        """Return *True* if *event* passes all checks."""
        ok, _ = self.validate(event)
        return ok

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @staticmethod
    def _normalise(check: Any) -> Optional[Callable[[Any], bool]]:
        if check is None:
            return None
        if isinstance(check, type) or (
            isinstance(check, tuple) and all(isinstance(c, type) for c in check)
        ):
            return lambda v, t=check: isinstance(v, t)
        if callable(check):
            return check
        raise TypeError(f"check must be a type, tuple of types, or callable; got {check!r}")
