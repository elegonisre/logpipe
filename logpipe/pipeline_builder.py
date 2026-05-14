"""Convenience builder that wires a DirectoryWatcher into a Pipeline."""

import time
import logging
from typing import Optional

from logpipe.watcher import DirectoryWatcher
from logpipe.pipeline import Pipeline
from logpipe.sink import BaseSink
from logpipe.filter import Filter

logger = logging.getLogger(__name__)


class PipelineBuilder:
    """Fluent builder for constructing a watched pipeline.

    Example::

        sink = StdoutSink()
        (
            PipelineBuilder()
            .watch("/var/log/app/*.log")
            .with_sink(sink)
            .with_extra({"host": "web-01"})
            .build()
            .run(poll_interval=1.0)
        )
    """

    def __init__(self) -> None:
        self._pattern: Optional[str] = None
        self._sink: Optional[BaseSink] = None
        self._extra: dict = {}
        self._filter: Optional[Filter] = None

    def watch(self, pattern: str) -> "PipelineBuilder":
        """Set the glob pattern used to discover log files."""
        self._pattern = pattern
        return self

    def with_sink(self, sink: BaseSink) -> "PipelineBuilder":
        self._sink = sink
        return self

    def with_extra(self, extra: dict) -> "PipelineBuilder":
        self._extra = extra
        return self

    def with_filter(self, filt: Filter) -> "PipelineBuilder":
        self._filter = filt
        return self

    def build(self) -> "WatchedPipeline":
        if self._pattern is None:
            raise ValueError("A glob pattern must be set via .watch()")
        if self._sink is None:
            raise ValueError("A sink must be set via .with_sink()")
        return WatchedPipeline(
            pattern=self._pattern,
            sink=self._sink,
            extra=self._extra,
            filt=self._filter,
        )


class WatchedPipeline:
    """A pipeline that auto-discovers new files via a DirectoryWatcher."""

    def __init__(self, pattern: str, sink: BaseSink, extra: dict, filt: Optional[Filter]) -> None:
        self._sink = sink
        self._extra = extra
        self._filt = filt
        self._pipelines: dict = {}

        self._watcher = DirectoryWatcher(pattern, self._register_file)

    def _register_file(self, path: str) -> None:
        pipeline = Pipeline(path, self._sink, extra=self._extra)
        if self._filt is not None:
            pipeline.set_filter(self._filt)
        self._pipelines[path] = pipeline
        logger.info("registered pipeline for %s", path)

    def run(self, poll_interval: float = 1.0, max_iterations: Optional[int] = None) -> None:
        """Run the watched pipeline loop.

        Args:
            poll_interval: Seconds to sleep between scan+process cycles.
            max_iterations: Stop after this many iterations (useful for tests).
        """
        iterations = 0
        while True:
            self._watcher.scan()
            for pipeline in list(self._pipelines.values()):
                pipeline.run_once()
            iterations += 1
            if max_iterations is not None and iterations >= max_iterations:
                break
            time.sleep(poll_interval)
