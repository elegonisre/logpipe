"""FanoutSink — broadcasts every event to multiple child sinks."""

from __future__ import annotations

from typing import Iterable

from logpipe.sink import BaseSink


class FanoutSink(BaseSink):
    """Write each event to every sink in the fan-out list.

    Parameters
    ----------
    sinks:
        An iterable of :class:`BaseSink` instances that will receive every
        event forwarded to this sink.  The list may be empty, in which case
        events are silently discarded.
    stop_on_error:
        When *True* (default), the first sink that raises will abort
        delivery to subsequent sinks and re-raise the exception.  When
        *False*, errors from individual sinks are collected and a
        ``RuntimeError`` summarising all failures is raised after all sinks
        have been attempted.
    """

    def __init__(
        self,
        sinks: Iterable[BaseSink] = (),
        *,
        stop_on_error: bool = True,
    ) -> None:
        self._sinks: list[BaseSink] = list(sinks)
        self._stop_on_error = stop_on_error

    # ------------------------------------------------------------------
    # Public helpers
    # ------------------------------------------------------------------

    def add(self, sink: BaseSink) -> "FanoutSink":
        """Append *sink* to the fan-out list and return *self* for chaining."""
        if not isinstance(sink, BaseSink):
            raise TypeError(f"Expected a BaseSink, got {type(sink).__name__!r}")
        self._sinks.append(sink)
        return self

    @property
    def sinks(self) -> list[BaseSink]:
        """Read-only view of the current sink list."""
        return list(self._sinks)

    # ------------------------------------------------------------------
    # BaseSink interface
    # ------------------------------------------------------------------

    def write(self, event: dict) -> None:  # type: ignore[override]
        if self._stop_on_error:
            for sink in self._sinks:
                sink.write(event)
            return

        errors: list[str] = []
        for sink in self._sinks:
            try:
                sink.write(event)
            except Exception as exc:  # noqa: BLE001
                errors.append(f"{type(sink).__name__}: {exc}")

        if errors:
            raise RuntimeError(
                "FanoutSink: {} child sink(s) failed:\n{}".format(
                    len(errors), "\n".join(f"  - {e}" for e in errors)
                )
            )

    def flush(self) -> None:
        """Flush all child sinks."""
        for sink in self._sinks:
            sink.flush()
