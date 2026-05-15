"""A Pipeline subclass that records metrics for every processed event."""
from __future__ import annotations

from typing import Dict, List, Optional

from logpipe.metrics import Metrics, default_metrics
from logpipe.pipeline import Pipeline
from logpipe.sink import BaseSink
from logpipe.filter import Filter


class InstrumentedPipeline(Pipeline):
    """Wraps :class:`Pipeline` and updates a :class:`Metrics` instance.

    Counters recorded
    -----------------
    ``lines_read``      – raw lines consumed from all tailers
    ``events_parsed``   – lines that produced a structured event
    ``events_dropped``  – events rejected by the active filter
    ``events_forwarded``– events forwarded to the sink
    ``parse_errors``    – lines that could not be parsed
    """

    def __init__(
        self,
        paths: List[str],
        sink: BaseSink,
        extra: Optional[Dict] = None,
        metrics: Optional[Metrics] = None,
    ) -> None:
        super().__init__(paths, sink, extra)
        self._metrics: Metrics = metrics if metrics is not None else default_metrics

    # ------------------------------------------------------------------
    # Override the hot path
    # ------------------------------------------------------------------

    def run_once(self) -> int:
        """Process one round of tailing; return the number of events forwarded."""
        forwarded = 0
        for tailer in self._tailers:  # type: ignore[attr-defined]
            for line in tailer.tail():
                self._metrics.increment("lines_read")
                event = self._parse(line)  # type: ignore[attr-defined]
                if event is None:
                    self._metrics.increment("parse_errors")
                    continue
                self._metrics.increment("events_parsed")
                if self._filter and not self._filter.match(event):  # type: ignore[attr-defined]
                    self._metrics.increment("events_dropped")
                    continue
                enriched = {**event, **(self._extra or {})}  # type: ignore[attr-defined]
                self._sink.write(enriched)  # type: ignore[attr-defined]
                self._metrics.increment("events_forwarded")
                forwarded += 1
        self._metrics.set_gauge("last_run_forwarded", forwarded)
        return forwarded
