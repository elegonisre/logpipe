"""Tests for logpipe.fanout_sink.FanoutSink."""

from __future__ import annotations

import pytest

from logpipe.fanout_sink import FanoutSink
from logpipe.sink import MemorySink


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_sinks(n: int = 2) -> list[MemorySink]:
    return [MemorySink() for _ in range(n)]


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_empty_fanout_accepts_events_silently():
    fanout = FanoutSink()
    fanout.write({"msg": "hello"})  # should not raise


def test_sinks_property_returns_copy():
    children = _make_sinks(3)
    fanout = FanoutSink(children)
    result = fanout.sinks
    assert result == children
    result.clear()  # mutating the copy must not affect internal list
    assert len(fanout.sinks) == 3


def test_add_returns_self_for_chaining():
    fanout = FanoutSink()
    s = MemorySink()
    assert fanout.add(s) is fanout


def test_add_non_sink_raises():
    fanout = FanoutSink()
    with pytest.raises(TypeError, match="BaseSink"):
        fanout.add(object())  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Write fan-out
# ---------------------------------------------------------------------------


def test_write_broadcasts_to_all_sinks():
    children = _make_sinks(3)
    fanout = FanoutSink(children)
    event = {"level": "info", "msg": "broadcast"}
    fanout.write(event)
    for child in children:
        assert child.events == [event]


def test_write_delivers_multiple_events_in_order():
    children = _make_sinks(2)
    fanout = FanoutSink(children)
    events = [{"n": i} for i in range(5)]
    for ev in events:
        fanout.write(ev)
    for child in children:
        assert child.events == events


# ---------------------------------------------------------------------------
# Error handling — stop_on_error=True (default)
# ---------------------------------------------------------------------------


def test_stop_on_error_aborts_on_first_failure():
    good1 = MemorySink()
    good2 = MemorySink()

    class _BadSink(MemorySink):
        def write(self, event):
            raise RuntimeError("boom")

    bad = _BadSink()
    fanout = FanoutSink([good1, bad, good2], stop_on_error=True)
    with pytest.raises(RuntimeError, match="boom"):
        fanout.write({"x": 1})
    assert good1.events == [{"x": 1}]
    assert good2.events == []  # never reached


# ---------------------------------------------------------------------------
# Error handling — stop_on_error=False
# ---------------------------------------------------------------------------


def test_continue_on_error_attempts_all_sinks():
    good = MemorySink()

    class _BadSink(MemorySink):
        def write(self, event):
            raise ValueError("nope")

    bad1, bad2 = _BadSink(), _BadSink()
    fanout = FanoutSink([bad1, good, bad2], stop_on_error=False)
    with pytest.raises(RuntimeError, match="2 child sink"):
        fanout.write({"y": 2})
    assert good.events == [{"y": 2}]  # good sink still received the event


# ---------------------------------------------------------------------------
# Flush
# ---------------------------------------------------------------------------


def test_flush_calls_flush_on_all_children():
    flushed: list[int] = []

    class _TrackFlush(MemorySink):
        def __init__(self, idx):
            super().__init__()
            self._idx = idx

        def flush(self):
            flushed.append(self._idx)

    fanout = FanoutSink([_TrackFlush(0), _TrackFlush(1), _TrackFlush(2)])
    fanout.flush()
    assert flushed == [0, 1, 2]
