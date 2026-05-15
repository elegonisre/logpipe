"""Pipeline wrapper that drops throttled events before forwarding to a sink."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logpipe.parser import parse_line
from logpipe.sink import BaseSink
from logpipe.tailer import FileTailer
from logpipe.throttle import Throttle


class ThrottledPipeline:
    """Wrap a :class:`~logpipe.tailer.FileTailer` with per-topic throttling.

    Parameters
    ----------
    tailer:
        Source of raw log lines.
    sink:
        Destination for allowed events.
    throttle:
        :class:`Throttle` instance that decides whether each event passes.
    extra:
        Static fields merged into every forwarded event.
    """

    def __init__(
        self,
        tailer: FileTailer,
        sink: BaseSink,
        throttle: Throttle,
        extra: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._tailer = tailer
        self._sink = sink
        self._throttle = throttle
        self._extra: Dict[str, Any] = extra or {}
        self._forwarded = 0
        self._dropped = 0

    # ------------------------------------------------------------------
    # Counters
    # ------------------------------------------------------------------

    @property
    def forwarded(self) -> int:
        """Total events forwarded since instantiation."""
        return self._forwarded

    @property
    def dropped(self) -> int:
        """Total events suppressed by the throttle since instantiation."""
        return self._dropped

    # ------------------------------------------------------------------
    # Core
    # ------------------------------------------------------------------

    def run_once(self, lines: Optional[List[str]] = None) -> int:
        """Process *lines* (or the next batch from the tailer).

        Returns the number of events forwarded.
        """
        if lines is None:
            lines = list(self._tailer.tail())

        forwarded = 0
        for raw in lines:
            event = parse_line(raw)
            if event is None:
                continue
            if self._extra:
                event = {**self._extra, **event}
            if self._throttle.allow(event):
                self._sink.write(event)
                self._forwarded += 1
                forwarded += 1
            else:
                self._dropped += 1

        self._sink.flush()
        return forwarded
