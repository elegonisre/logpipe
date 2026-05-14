"""Pipeline: wires tailer → parser → filter → sink."""

import threading
import time
from typing import Any, Dict, List, Optional

from logpipe.filter import Filter
from logpipe.parser import parse_line
from logpipe.sink import BaseSink
from logpipe.tailer import FileTailer

Event = Dict[str, Any]


class Pipeline:
    """Reads lines from one or more files, parses them, filters, then sinks."""

    def __init__(
        self,
        paths: List[str],
        sink: BaseSink,
        extra_fields: Optional[Dict[str, Any]] = None,
        poll_interval: float = 0.1,
        event_filter: Optional[Filter] = None,
    ) -> None:
        self._tailers = [FileTailer(p) for p in paths]
        self._sink = sink
        self._extra = extra_fields or {}
        self._poll_interval = poll_interval
        self._filter: Filter = event_filter or Filter()
        self._running = False
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def set_filter(self, event_filter: Filter) -> None:
        """Replace the active filter at runtime."""
        self._filter = event_filter

    def run_once(self) -> int:
        """Drain all tailers once; return the number of events forwarded."""
        forwarded = 0
        for tailer in self._tailers:
            for line in tailer.tail():
                event = parse_line(line)
                if event is None:
                    continue
                event.update(self._extra)
                if not self._filter.match(event):
                    continue
                self._sink.write(event)
                forwarded += 1
        self._sink.flush()
        return forwarded

    def start(self) -> None:
        """Start background polling thread."""
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self) -> None:
        """Stop background polling thread and wait for it to finish."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
            self._thread = None

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        while self._running:
            self.run_once()
            time.sleep(self._poll_interval)
