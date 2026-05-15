"""A Pipeline wrapper that samples events before forwarding them to the sink."""
from __future__ import annotations

from typing import Any, Dict, List, Optional

from logpipe.pipeline import Pipeline
from logpipe.sampler import Sampler
from logpipe.sink import BaseSink

Event = Dict[str, Any]


class SampledPipeline:
    """Wraps a :class:`~logpipe.pipeline.Pipeline` and applies a
    :class:`~logpipe.sampler.Sampler` to every parsed event before it
    reaches the sink.

    Parameters
    ----------
    pipeline:
        The underlying pipeline to delegate parsing and tailing to.
    sampler:
        A configured :class:`Sampler` instance.
    """

    def __init__(self, pipeline: Pipeline, sampler: Sampler) -> None:
        self._pipeline = pipeline
        self._sampler = sampler
        self._dropped: int = 0
        self._forwarded: int = 0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def dropped(self) -> int:
        """Total number of events dropped by the sampler."""
        return self._dropped

    @property
    def forwarded(self) -> int:
        """Total number of events forwarded to the sink."""
        return self._forwarded

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def run_once(self, sink: BaseSink, extra: Optional[Dict[str, Any]] = None) -> List[Event]:
        """Run one iteration of the pipeline and return the *forwarded* events.

        Parsed events that are rejected by the sampler are counted in
        :attr:`dropped` and never reach *sink*.
        """
        from logpipe.sink import MemorySink  # local import to avoid cycles

        # Collect all events the underlying pipeline would normally emit.
        staging: MemorySink = MemorySink()
        self._pipeline.run_once(staging, extra=extra)

        forwarded: List[Event] = []
        for event in staging.events:
            if self._sampler.should_keep(event):
                sink.write(event)
                forwarded.append(event)
                self._forwarded += 1
            else:
                self._dropped += 1

        return forwarded

    def reset_stats(self) -> None:
        """Reset forwarded/dropped counters and the sampler state."""
        self._dropped = 0
        self._forwarded = 0
        self._sampler.reset()
