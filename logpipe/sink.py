"""Sink implementations for logpipe.

A sink receives parsed log events (plain dicts) and persists or forwards them.
All sinks share the BaseSink interface: ``write(event)`` and ``flush()``.
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from typing import Any, Dict, IO, List, Optional


class BaseSink:
    """Abstract base — subclasses must implement ``write``."""

    def write(self, event: Dict[str, Any]) -> None:  # pragma: no cover
        raise NotImplementedError

    def flush(self) -> None:
        """Optional flush; no-op by default."""


def _serialise(event: Dict[str, Any]) -> str:
    """Return a compact JSON line for *event*, falling back to str() for
    values that are not JSON-serialisable."""
    try:
        return json.dumps(event, separators=(",", ":"))
    except (TypeError, ValueError):
        safe = {k: v if isinstance(v, (str, int, float, bool, type(None))) else str(v)
                for k, v in event.items()}
        return json.dumps(safe, separators=(",", ":"))


class StdoutSink(BaseSink):
    """Write one JSON line per event to *stdout*."""

    def __init__(self, stream: Optional[IO[str]] = None) -> None:
        self._stream = stream or sys.stdout

    def write(self, event: Dict[str, Any]) -> None:
        self._stream.write(_serialise(event) + "\n")

    def flush(self) -> None:
        self._stream.flush()


class FileSink(BaseSink):
    """Append one JSON line per event to a file on disk."""

    def __init__(self, path: str | Path) -> None:
        self._path = Path(path)
        self._fh = self._path.open("a", encoding="utf-8")

    def write(self, event: Dict[str, Any]) -> None:
        self._fh.write(_serialise(event) + "\n")

    def flush(self) -> None:
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()


class MemorySink(BaseSink):
    """Collect events in memory — useful for testing."""

    def __init__(self) -> None:
        self.events: List[Dict[str, Any]] = []

    def write(self, event: Dict[str, Any]) -> None:
        self.events.append(event)

    def flush(self) -> None:
        pass  # nothing to flush
