"""RetriedPipeline — Pipeline variant that wraps its sink in a RetrySink."""
from __future__ import annotations

from typing import Any

from logpipe.pipeline import Pipeline
from logpipe.retry_sink import RetrySink
from logpipe.sink import BaseSink
from logpipe.tailer import FileTailer


class RetriedPipeline:
    """Thin wrapper around :class:`Pipeline` that installs a :class:`RetrySink`
    around *sink* so transient write errors are handled transparently.

    Parameters
    ----------
    path:        Log file to tail.
    sink:        Destination sink (will be wrapped).
    max_retries: Passed through to :class:`RetrySink`.
    backoff:     Passed through to :class:`RetrySink`.
    extra:       Static fields merged into every parsed event.
    """

    def __init__(
        self,
        path: str,
        sink: BaseSink,
        *,
        max_retries: int = 3,
        backoff: float = 0.1,
        extra: dict[str, Any] | None = None,
    ) -> None:
        self._retry_sink = RetrySink(sink, max_retries=max_retries, backoff=backoff)
        tailer = FileTailer(path)
        self._pipeline = Pipeline(tailer, self._retry_sink, extra=extra or {})

    # ------------------------------------------------------------------
    # Delegation helpers
    # ------------------------------------------------------------------

    @property
    def attempts(self) -> int:
        """Total write attempts made by the underlying :class:`RetrySink`."""
        return self._retry_sink.attempts

    @property
    def failures(self) -> int:
        """Events permanently dropped after exhausting retries."""
        return self._retry_sink.failures

    def set_filter(self, f: Any) -> None:  # noqa: ANN401
        self._pipeline.set_filter(f)

    def run_once(self) -> int:
        """Process all currently available lines; return the count parsed."""
        return self._pipeline.run_once()

    def start(self, poll_interval: float = 0.5) -> None:  # pragma: no cover
        """Run the pipeline in a blocking loop."""
        self._pipeline.start(poll_interval=poll_interval)
