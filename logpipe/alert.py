"""Simple threshold-based alerting for log pipeline metrics."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional


@dataclass
class AlertRule:
    name: str
    metric: str
    threshold: float
    comparator: str  # 'gt', 'lt', 'gte', 'lte', 'eq'
    message: str
    cooldown: float = 60.0  # seconds between repeated alerts
    _last_fired: Optional[float] = field(default=None, repr=False)

    _COMPARATORS = {
        "gt": lambda v, t: v > t,
        "lt": lambda v, t: v < t,
        "gte": lambda v, t: v >= t,
        "lte": lambda v, t: v <= t,
        "eq": lambda v, t: v == t,
    }

    def __post_init__(self) -> None:
        if self.comparator not in self._COMPARATORS:
            raise ValueError(
                f"Unknown comparator '{self.comparator}'. "
                f"Choose from: {list(self._COMPARATORS)}"
            )
        if self.cooldown < 0:
            raise ValueError("cooldown must be >= 0")

    def evaluate(self, value: float) -> bool:
        return self._COMPARATORS[self.comparator](value, self.threshold)


class AlertManager:
    """Evaluates AlertRules against current metric values and fires callbacks."""

    def __init__(self, clock: Optional[Callable[[], float]] = None) -> None:
        import time
        self._clock: Callable[[], float] = clock or time.monotonic
        self._rules: List[AlertRule] = []
        self._handlers: List[Callable[[AlertRule, float], None]] = []
        self._fire_counts: Dict[str, int] = {}

    def add_rule(self, rule: AlertRule) -> "AlertManager":
        self._rules.append(rule)
        self._fire_counts.setdefault(rule.name, 0)
        return self

    def on_alert(self, handler: Callable[[AlertRule, float], None]) -> "AlertManager":
        """Register a callback invoked when a rule fires."""
        self._handlers.append(handler)
        return self

    def evaluate(self, metrics: Dict[str, float]) -> int:
        """Check all rules against *metrics*. Returns number of alerts fired."""
        fired = 0
        now = self._clock()
        for rule in self._rules:
            value = metrics.get(rule.metric)
            if value is None:
                continue
            if not rule.evaluate(value):
                continue
            if rule._last_fired is not None:
                if now - rule._last_fired < rule.cooldown:
                    continue
            rule._last_fired = now
            self._fire_counts[rule.name] = self._fire_counts.get(rule.name, 0) + 1
            for handler in self._handlers:
                handler(rule, value)
            fired += 1
        return fired

    def fire_count(self, rule_name: str) -> int:
        return self._fire_counts.get(rule_name, 0)

    def reset(self) -> None:
        for rule in self._rules:
            rule._last_fired = None
        self._fire_counts = {rule.name: 0 for rule in self._rules}
