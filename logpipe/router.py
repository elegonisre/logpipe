"""Route parsed log events to one or more sinks based on field matching."""

from __future__ import annotations

from typing import Callable, Dict, List, Optional, Tuple

from logpipe.sink import BaseSink


Predicate = Callable[[Dict], bool]


class Router:
    """Forward events to registered sinks, optionally filtered by a predicate.

    Usage::

        router = Router(default_sink=stdout_sink)
        router.add_route(lambda e: e.get("level") == "error", error_sink)
        router.dispatch({"level": "error", "msg": "boom"})
    """

    def __init__(self, default_sink: Optional[BaseSink] = None) -> None:
        self._routes: List[Tuple[Predicate, BaseSink]] = []
        self._default_sink = default_sink

    def add_route(self, predicate: Predicate, sink: BaseSink) -> "Router":
        """Register *sink* to receive events that satisfy *predicate*.

        Returns self to allow chaining.
        """
        self._routes.append((predicate, sink))
        return self

    def set_default(self, sink: BaseSink) -> "Router":
        """Set a catch-all sink for events not matched by any route."""
        self._default_sink = sink
        return self

    def dispatch(self, event: Dict) -> int:
        """Send *event* to every matching sink.

        Returns the number of sinks the event was forwarded to.  If no route
        matches and a default sink is configured, the event goes there.
        """
        matched = 0
        for predicate, sink in self._routes:
            try:
                if predicate(event):
                    sink.write(event)
                    matched += 1
            except Exception:
                # A broken predicate must never drop subsequent routes.
                pass

        if matched == 0 and self._default_sink is not None:
            self._default_sink.write(event)
            matched = 1

        return matched

    def flush_all(self) -> None:
        """Flush every registered sink plus the default sink."""
        seen: List[BaseSink] = []
        for _, sink in self._routes:
            if sink not in seen:
                sink.flush()
                seen.append(sink)
        if self._default_sink is not None and self._default_sink not in seen:
            self._default_sink.flush()
