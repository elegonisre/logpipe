"""Pipeline: wires together a FileTailer, a line parser, and a sink."""

from __future__ import annotations

import logging
import threading
from typing import Callable, Dict, Any, Optional

from logpipe.tailer import FileTailer
from logpipe.parser import parse_line
from logpipe.sink import BaseSink

logger = logging.getLogger(__name__)


class Pipeline:
    """Tail *path*, parse each line, and forward events to *sink*.

    Parameters
    ----------
    path:
        Absolute or relative path to the log file being tailed.
    sink:
        Any :class:`~logpipe.sink.BaseSink` implementation.
    extra:
        Static key/value pairs merged into every emitted event
        (e.g. ``{"source": "app", "host": "web-01"}``).
    poll_interval:
        Seconds between tail polls (forwarded to :class:`FileTailer`).
    """

    def __init__(
        self,
        path: str,
        sink: BaseSink,
        extra: Optional[Dict[str, Any]] = None,
        poll_interval: float = 0.5,
    ) -> None:
        self.path = path
        self.sink = sink
        self.extra: Dict[str, Any] = extra or {}
        self._tailer = FileTailer(path, poll_interval=poll_interval)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self) -> int:
        """Drain all currently available lines and return the count emitted."""
        count = 0
        for line in self._tailer.tail(stop_event=self._stop_event):
            event = self._process(line)
            if event is not None:
                self.sink.write(event)
                count += 1
        self.sink.flush()
        return count

    def start(self) -> None:
        """Start tailing in a background daemon thread."""
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(target=self._loop, daemon=True, name=f"pipeline:{self.path}")
        self._thread.start()
        logger.info("Pipeline started for %s", self.path)

    def stop(self, timeout: float = 5.0) -> None:
        """Signal the background thread to stop and wait for it."""
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=timeout)
        self.sink.flush()
        logger.info("Pipeline stopped for %s", self.path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _loop(self) -> None:
        for line in self._tailer.tail(stop_event=self._stop_event):
            event = self._process(line)
            if event is not None:
                self.sink.write(event)

    def _process(self, line: str) -> Optional[Dict[str, Any]]:
        event = parse_line(line)
        if event is None:
            logger.debug("Unparseable line skipped: %r", line)
            return None
        if self.extra:
            event = {**self.extra, **event}
        return event
