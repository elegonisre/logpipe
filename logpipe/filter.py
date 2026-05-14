"""Event filtering support for logpipe pipelines."""

from typing import Any, Callable, Dict, List, Optional

Event = Dict[str, Any]
Predicate = Callable[[Event], bool]


class Filter:
    """Chains multiple predicate functions and applies them to events."""

    def __init__(self, predicates: Optional[List[Predicate]] = None) -> None:
        self._predicates: List[Predicate] = list(predicates or [])

    def add(self, predicate: Predicate) -> "Filter":
        """Register an additional predicate. Returns self for chaining."""
        self._predicates.append(predicate)
        return self

    def match(self, event: Event) -> bool:
        """Return True only if *all* predicates accept the event."""
        return all(p(event) for p in self._predicates)

    def apply(self, events: List[Event]) -> List[Event]:
        """Return the subset of *events* that pass all predicates."""
        return [e for e in events if self.match(e)]


# ---------------------------------------------------------------------------
# Built-in predicate factories
# ---------------------------------------------------------------------------

def has_field(key: str) -> Predicate:
    """Accept events that contain *key*."""
    return lambda event: key in event


def field_equals(key: str, value: Any) -> Predicate:
    """Accept events where event[key] == value."""
    return lambda event: event.get(key) == value


def field_contains(key: str, substring: str) -> Predicate:
    """Accept events where str(event[key]) contains *substring*."""
    return lambda event: substring in str(event.get(key, ""))


def min_level(level: str, order: Optional[List[str]] = None) -> Predicate:
    """Accept events whose 'level' field is >= *level* in *order*."""
    _order = order or ["debug", "info", "warning", "error", "critical"]
    threshold = _order.index(level.lower()) if level.lower() in _order else 0

    def _predicate(event: Event) -> bool:
        lvl = str(event.get("level", "")).lower()
        return _order.index(lvl) >= threshold if lvl in _order else False

    return _predicate
