"""Pipeline wrapper that evaluates AlertRules after every run_once cycle."""
from __future__ import annotations

from typing import Dict, Optional

from logpipe.alert import AlertManager
from logpipe.instrumented_pipeline import InstrumentedPipeline
from logpipe.metrics import Metrics


class AlertedPipeline:
    """Wraps InstrumentedPipeline and fires alerts based on collected metrics.

    Example usage::

        from logpipe.alert import AlertManager, AlertRule
        from logpipe.alerted_pipeline import AlertedPipeline

        mgr = AlertManager()
        mgr.add_rule(AlertRule(
            name="too_many_errors",
            metric="lines_read",
            threshold=1000,
            comparator="gt",
            message="High log volume detected",
        ))
        mgr.on_alert(lambda rule, val: print(f"ALERT {rule.name}: {val}"))

        pipeline = AlertedPipeline(inner, metrics, mgr)
        pipeline.run_once()
    """

    def __init__(
        self,
        inner: InstrumentedPipeline,
        metrics: Metrics,
        alert_manager: AlertManager,
        extra_gauges: Optional[Dict[str, float]] = None,
    ) -> None:
        self._inner = inner
        self._metrics = metrics
        self._alert_manager = alert_manager
        self._extra_gauges: Dict[str, float] = extra_gauges or {}
        self._alerts_fired: int = 0

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def alerts_fired(self) -> int:
        """Cumulative number of alert firings since creation."""
        return self._alerts_fired

    def run_once(self) -> None:
        """Run the inner pipeline then evaluate alert rules."""
        self._inner.run_once()
        snapshot = self._build_snapshot()
        fired = self._alert_manager.evaluate(snapshot)
        self._alerts_fired += fired

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_snapshot(self) -> Dict[str, float]:
        """Merge metrics counters/gauges with any extra gauges provided."""
        snapshot: Dict[str, float] = {}
        for name in self._metrics.counter_names():
            snapshot[name] = float(self._metrics.counter(name))
        for name in self._metrics.gauge_names():
            snapshot[name] = self._metrics.gauge(name)
        snapshot.update(self._extra_gauges)
        return snapshot
