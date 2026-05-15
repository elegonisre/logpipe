"""Fluent builder for constructing a Pipeline with optional components."""
from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

from logpipe.filter import Filter
from logpipe.pipeline import Pipeline
from logpipe.sink import BaseSink, StdoutSink
from logpipe.transformer import Transformer


class PipelineBuilder:
    """Construct a :class:`~logpipe.pipeline.Pipeline` step by step.

    Example::

        pipeline = (
            PipelineBuilder()
            .watch("/var/log/app.log")
            .with_sink(my_sink)
            .with_extra(env="prod")
            .with_transformer(Transformer().mask_field("password"))
            .build()
        )
    """

    def __init__(self) -> None:
        self._paths: List[Path] = []
        self._sink: Optional[BaseSink] = None
        self._extra: Dict[str, Any] = {}
        self._filter: Optional[Filter] = None
        self._transformer: Optional[Transformer] = None

    # ------------------------------------------------------------------
    # Configuration
    # ------------------------------------------------------------------

    def watch(self, *paths: str) -> "PipelineBuilder":
        """Add one or more file paths to tail."""
        for p in paths:
            self._paths.append(Path(p))
        return self

    def with_sink(self, sink: BaseSink) -> "PipelineBuilder":
        """Set the destination sink (default: :class:`~logpipe.sink.StdoutSink`)."""
        self._sink = sink
        return self

    def with_extra(self, **kwargs: Any) -> "PipelineBuilder":
        """Merge static key/value pairs into every emitted event."""
        self._extra.update(kwargs)
        return self

    def with_filter(self, f: Filter) -> "PipelineBuilder":
        """Attach a :class:`~logpipe.filter.Filter` to the pipeline."""
        self._filter = f
        return self

    def with_transformer(self, transformer: Transformer) -> "PipelineBuilder":
        """Attach a :class:`~logpipe.transformer.Transformer` to the pipeline."""
        self._transformer = transformer
        return self

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(self) -> Pipeline:
        """Validate configuration and return a ready :class:`~logpipe.pipeline.Pipeline`."""
        if not self._paths:
            raise ValueError("PipelineBuilder: at least one path must be provided via .watch()")

        sink = self._sink if self._sink is not None else StdoutSink()

        pipeline = Pipeline(
            paths=[str(p) for p in self._paths],
            sink=sink,
            extra=self._extra,
        )

        if self._filter is not None:
            pipeline.set_filter(self._filter)

        if self._transformer is not None:
            pipeline.set_transformer(self._transformer)

        return pipeline
