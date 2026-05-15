"""Tests for logpipe.retry_sink.RetrySink."""
from __future__ import annotations

import pytest
from unittest.mock import MagicMock, call

from logpipe.retry_sink import RetrySink
from logpipe.sink import MemorySink


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

def test_negative_max_retries_raises():
    inner = MemorySink()
    with pytest.raises(ValueError, match="max_retries"):
        RetrySink(inner, max_retries=-1)


def test_negative_backoff_raises():
    inner = MemorySink()
    with pytest.raises(ValueError, match="backoff"):
        RetrySink(inner, backoff=-0.1)


# ---------------------------------------------------------------------------
# Happy-path: successful write on first attempt
# ---------------------------------------------------------------------------

def test_successful_write_reaches_inner_sink():
    inner = MemorySink()
    sink = RetrySink(inner, max_retries=2, backoff=0)
    sink.write({"level": "info", "msg": "hello"})
    assert inner.events == [{"level": "info", "msg": "hello"}]


def test_attempts_incremented_on_success():
    inner = MemorySink()
    sink = RetrySink(inner, max_retries=2, backoff=0)
    sink.write({"x": 1})
    sink.write({"x": 2})
    assert sink.attempts == 2
    assert sink.failures == 0


# ---------------------------------------------------------------------------
# Retry behaviour
# ---------------------------------------------------------------------------

def test_retries_on_transient_failure(monkeypatch):
    monkeypatch.setattr("logpipe.retry_sink.time.sleep", lambda _: None)
    call_count = 0
    inner = MagicMock()

    def flaky_write(event):
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise IOError("transient")

    inner.write.side_effect = flaky_write
    sink = RetrySink(inner, max_retries=3, backoff=0.01)
    sink.write({"msg": "test"})

    assert call_count == 3
    assert sink.attempts == 3
    assert sink.failures == 0


def test_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr("logpipe.retry_sink.time.sleep", lambda _: None)
    inner = MagicMock()
    inner.write.side_effect = RuntimeError("always fails")

    sink = RetrySink(inner, max_retries=2, backoff=0)
    sink.write({"msg": "doomed"})

    assert sink.attempts == 3          # 1 initial + 2 retries
    assert sink.failures == 1
    assert inner.write.call_count == 3


def test_failure_does_not_raise():
    """RetrySink must swallow the final exception and only log it."""
    inner = MagicMock()
    inner.write.side_effect = ValueError("boom")
    sink = RetrySink(inner, max_retries=1, backoff=0)
    # Should NOT raise
    sink.write({"msg": "quiet fail"})
    assert sink.failures == 1


def test_multiple_events_independent_retry_counts(monkeypatch):
    monkeypatch.setattr("logpipe.retry_sink.time.sleep", lambda _: None)
    inner = MemorySink()
    sink = RetrySink(inner, max_retries=2, backoff=0)
    for i in range(5):
        sink.write({"i": i})
    assert len(inner.events) == 5
    assert sink.failures == 0


# ---------------------------------------------------------------------------
# Flush delegation
# ---------------------------------------------------------------------------

def test_flush_delegates_to_inner():
    inner = MagicMock()
    sink = RetrySink(inner)
    sink.flush()
    inner.flush.assert_called_once()
