"""Sink abstractions — destinations for parsed log events."""

import json
import sys
from abc import ABC, abstractmethod
from typing import Any, TextIO


class BaseSink(ABC):
    """All sinks must implement :meth:`write`."""

    @abstractmethod
    def write(self, event: dict[str, Any]) -> None:
        """Persist or forward a single structured *event*."""

    def flush(self) -> None:  # noqa: B027  (intentionally empty default)
        """Optional: flush any internal buffers."""


class StdoutSink(BaseSink):
    """Writes JSON-encoded events to *stream* (default: stdout)."""

    def __init__(self, stream: TextIO | None = None) -> None:
        self._stream: TextIO = stream or sys.stdout

    def write(self, event: dict[str, Any]) -> None:
        self._stream.write(json.dumps(event, default=str) + "\n")

    def flush(self) -> None:
        self._stream.flush()


class FileSink(BaseSink):
    """Appends JSON-encoded events to a file at *path*."""

    def __init__(self, path: str) -> None:
        self._path = path
        self._fh = open(path, "a", encoding="utf-8")  # noqa: SIM115

    def write(self, event: dict[str, Any]) -> None:
        self._fh.write(json.dumps(event, default=str) + "\n")

    def flush(self) -> None:
        self._fh.flush()

    def close(self) -> None:
        self._fh.close()

    def __enter__(self) -> "FileSink":
        return self

    def __exit__(self, *_: object) -> None:
        self.close()


class MemorySink(BaseSink):
    """Collects events in-memory — useful for testing."""

    def __init__(self) -> None:
        self.events: list[dict[str, Any]] = []

    def write(self, event: dict[str, Any]) -> None:
        self.events.append(event)
