"""Tests for logpipe.buffer.Buffer."""

from __future__ import annotations

import time

import pytest

from logpipe.buffer import Buffer


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

def test_invalid_max_size_raises():
    with pytest.raises(ValueError, match="max_size"):
        Buffer(max_size=0)


def test_invalid_max_age_raises():
    with pytest.raises(ValueError, match="max_age"):
        Buffer(max_age=0)


def test_negative_max_age_raises():
    with pytest.raises(ValueError, match="max_age"):
        Buffer(max_age=-1.0)


# ---------------------------------------------------------------------------
# Basic behaviour
# ---------------------------------------------------------------------------

def test_pending_starts_at_zero():
    buf = Buffer()
    assert buf.pending() == 0


def test_add_increases_pending():
    buf = Buffer(max_size=10)
    buf.add({"level": "info", "msg": "hello"})
    assert buf.pending() == 1


def test_flush_returns_events_and_resets():
    buf = Buffer(max_size=10)
    buf.add({"a": 1})
    buf.add({"b": 2})
    flushed = buf.flush()
    assert flushed == [{"a": 1}, {"b": 2}]
    assert buf.pending() == 0


def test_flush_empty_buffer_returns_empty_list():
    buf = Buffer()
    assert buf.flush() == []


# ---------------------------------------------------------------------------
# Auto-flush on size
# ---------------------------------------------------------------------------

def test_add_triggers_flush_when_max_size_reached():
    flushed_batches = []
    buf = Buffer(max_size=3, on_flush=flushed_batches.append)

    triggered = [buf.add({"i": i}) for i in range(3)]

    # The third add should have triggered a flush
    assert triggered[-1] is True
    assert len(flushed_batches) == 1
    assert len(flushed_batches[0]) == 3
    assert buf.pending() == 0


def test_add_does_not_trigger_flush_before_max_size():
    flushed_batches = []
    buf = Buffer(max_size=5, on_flush=flushed_batches.append)
    for i in range(4):
        buf.add({"i": i})
    assert flushed_batches == []
    assert buf.pending() == 4


# ---------------------------------------------------------------------------
# Auto-flush on age
# ---------------------------------------------------------------------------

def test_is_expired_false_when_fresh():
    buf = Buffer(max_age=60)
    assert buf.is_expired() is False


def test_is_expired_true_after_max_age(monkeypatch):
    start = time.monotonic()
    monkeypatch.setattr(time, "monotonic", lambda: start + 10)
    buf = Buffer(max_age=5)
    assert buf.is_expired() is True


def test_add_triggers_flush_when_expired(monkeypatch):
    start = time.monotonic()
    flushed = []
    buf = Buffer(max_size=100, max_age=5, on_flush=flushed.append)

    # First add at t=0 — not expired yet
    monkeypatch.setattr(time, "monotonic", lambda: start)
    buf.add({"first": True})
    assert flushed == []

    # Second add at t=6 — buffer is now expired
    monkeypatch.setattr(time, "monotonic", lambda: start + 6)
    triggered = buf.add({"second": True})
    assert triggered is True
    assert len(flushed) == 1
    assert len(flushed[0]) == 2


# ---------------------------------------------------------------------------
# on_flush callback
# ---------------------------------------------------------------------------

def test_on_flush_not_called_for_empty_flush():
    called = []
    buf = Buffer(on_flush=called.append)
    buf.flush()
    assert called == []


def test_no_on_flush_does_not_raise():
    buf = Buffer(max_size=2)
    buf.add({"x": 1})
    buf.add({"x": 2})  # triggers flush with no callback
    assert buf.pending() == 0
