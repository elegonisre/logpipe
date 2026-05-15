"""Tests for logpipe.throttle and logpipe.throttled_pipeline."""
from __future__ import annotations

import json
import os
import tempfile
from typing import List

import pytest

from logpipe.sink import MemorySink
from logpipe.tailer import FileTailer
from logpipe.throttle import Throttle
from logpipe.throttled_pipeline import ThrottledPipeline


# ---------------------------------------------------------------------------
# Throttle unit tests
# ---------------------------------------------------------------------------

def test_invalid_key_raises():
    with pytest.raises(ValueError):
        Throttle("", window=5)


def test_invalid_window_raises():
    with pytest.raises(ValueError):
        Throttle("msg", window=0)


def test_negative_window_raises():
    with pytest.raises(ValueError):
        Throttle("msg", window=-1)


def test_first_event_always_allowed():
    t = Throttle("msg", window=30)
    assert t.allow({"msg": "hello"}, _now=0.0) is True


def test_second_event_within_window_is_throttled():
    t = Throttle("msg", window=30)
    t.allow({"msg": "hello"}, _now=0.0)
    assert t.allow({"msg": "hello"}, _now=10.0) is False


def test_event_allowed_after_window_expires():
    t = Throttle("msg", window=30)
    t.allow({"msg": "hello"}, _now=0.0)
    assert t.allow({"msg": "hello"}, _now=30.0) is True


def test_different_topics_are_independent():
    t = Throttle("msg", window=30)
    t.allow({"msg": "a"}, _now=0.0)
    assert t.allow({"msg": "b"}, _now=5.0) is True


def test_event_without_key_is_always_allowed():
    t = Throttle("msg", window=30)
    assert t.allow({"level": "info"}, _now=0.0) is True
    assert t.allow({"level": "info"}, _now=1.0) is True


def test_reset_clears_all_topics():
    t = Throttle("msg", window=30)
    t.allow({"msg": "a"}, _now=0.0)
    t.allow({"msg": "b"}, _now=0.0)
    assert t.tracked() == 2
    t.reset()
    assert t.tracked() == 0
    assert t.allow({"msg": "a"}, _now=1.0) is True


def test_reset_specific_topic():
    t = Throttle("msg", window=30)
    t.allow({"msg": "a"}, _now=0.0)
    t.allow({"msg": "b"}, _now=0.0)
    t.reset("a")
    assert t.tracked() == 1
    assert t.allow({"msg": "a"}, _now=1.0) is True
    assert t.allow({"msg": "b"}, _now=1.0) is False


# ---------------------------------------------------------------------------
# ThrottledPipeline integration tests
# ---------------------------------------------------------------------------

def _write(path: str, lines: List[str]) -> None:
    with open(path, "w") as fh:
        for line in lines:
            fh.write(line + "\n")


def test_throttled_pipeline_forwards_first_event(tmp_path):
    log = str(tmp_path / "app.log")
    events = [{"msg": "error", "level": "error"}]
    _write(log, [json.dumps(e) for e in events])

    sink = MemorySink()
    tailer = FileTailer(log)
    throttle = Throttle("msg", window=60)
    pipeline = ThrottledPipeline(tailer, sink, throttle)

    forwarded = pipeline.run_once()
    assert forwarded == 1
    assert pipeline.dropped == 0
    assert len(sink.events) == 1


def test_throttled_pipeline_drops_repeated_event(tmp_path):
    log = str(tmp_path / "app.log")
    raw_lines = [json.dumps({"msg": "boom", "level": "error"})] * 3

    sink = MemorySink()
    tailer = FileTailer(log)
    throttle = Throttle("msg", window=60)
    pipeline = ThrottledPipeline(tailer, sink, throttle)

    forwarded = pipeline.run_once(lines=raw_lines)
    assert forwarded == 1
    assert pipeline.dropped == 2


def test_throttled_pipeline_merges_extra_fields(tmp_path):
    raw_lines = [json.dumps({"msg": "hi"})]
    sink = MemorySink()
    tailer = FileTailer(str(tmp_path / "x.log"))
    throttle = Throttle("msg", window=60)
    pipeline = ThrottledPipeline(tailer, sink, throttle, extra={"host": "srv1"})

    pipeline.run_once(lines=raw_lines)
    assert sink.events[0]["host"] == "srv1"


def test_throttled_pipeline_skips_unparseable_lines(tmp_path):
    raw_lines = ["not json or logfmt !!!###"]
    sink = MemorySink()
    tailer = FileTailer(str(tmp_path / "x.log"))
    throttle = Throttle("msg", window=60)
    pipeline = ThrottledPipeline(tailer, sink, throttle)

    forwarded = pipeline.run_once(lines=raw_lines)
    assert forwarded == 0
    assert len(sink.events) == 0
