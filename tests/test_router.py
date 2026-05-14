"""Tests for logpipe.router.Router."""

from __future__ import annotations

from typing import Dict, List

import pytest

from logpipe.router import Router
from logpipe.sink import MemorySink


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def _make_sinks(n: int = 2) -> List[MemorySink]:
    return [MemorySink() for _ in range(n)]


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------

def test_dispatch_to_matching_sink():
    errors, infos = _make_sinks()
    router = Router()
    router.add_route(lambda e: e.get("level") == "error", errors)
    router.add_route(lambda e: e.get("level") == "info", infos)

    router.dispatch({"level": "error", "msg": "bad"})
    router.dispatch({"level": "info", "msg": "ok"})

    assert len(errors.events) == 1
    assert len(infos.events) == 1


def test_dispatch_to_default_when_no_route_matches():
    default = MemorySink()
    router = Router(default_sink=default)
    router.add_route(lambda e: e.get("level") == "error", MemorySink())

    router.dispatch({"level": "debug", "msg": "verbose"})

    assert len(default.events) == 1
    assert default.events[0]["level"] == "debug"


def test_no_default_and_no_match_returns_zero():
    router = Router()
    router.add_route(lambda e: False, MemorySink())
    count = router.dispatch({"msg": "ignored"})
    assert count == 0


def test_event_dispatched_to_multiple_matching_sinks():
    a, b = _make_sinks()
    router = Router()
    router.add_route(lambda e: True, a)
    router.add_route(lambda e: True, b)

    count = router.dispatch({"msg": "broadcast"})

    assert count == 2
    assert len(a.events) == 1
    assert len(b.events) == 1


def test_broken_predicate_does_not_stop_other_routes():
    good = MemorySink()
    router = Router()
    router.add_route(lambda e: 1 / 0, MemorySink())  # raises ZeroDivisionError
    router.add_route(lambda e: True, good)

    count = router.dispatch({"msg": "hi"})

    assert count == 1
    assert len(good.events) == 1


def test_add_route_chaining():
    a, b = _make_sinks()
    router = Router()
    result = router.add_route(lambda e: True, a).add_route(lambda e: True, b)
    assert result is router


def test_set_default_chaining():
    default = MemorySink()
    router = Router()
    result = router.set_default(default)
    assert result is router


def test_flush_all_calls_every_sink(monkeypatch):
    flushed: List[str] = []

    class TrackingSink(MemorySink):
        def __init__(self, name: str) -> None:
            super().__init__()
            self._name = name

        def flush(self) -> None:
            flushed.append(self._name)

    a = TrackingSink("a")
    b = TrackingSink("b")
    default = TrackingSink("default")

    router = Router(default_sink=default)
    router.add_route(lambda e: True, a)
    router.add_route(lambda e: False, b)
    router.flush_all()

    assert set(flushed) == {"a", "b", "default"}
