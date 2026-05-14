"""Tests for logpipe.sink."""

import io
import json
import os
import tempfile

import pytest

from logpipe.sink import FileSink, MemorySink, StdoutSink


# ---------------------------------------------------------------------------
# MemorySink
# ---------------------------------------------------------------------------

def test_memory_sink_collects_events():
    sink = MemorySink()
    sink.write({"msg": "a"})
    sink.write({"msg": "b"})
    assert len(sink.events) == 2
    assert sink.events[0]["msg"] == "a"


# ---------------------------------------------------------------------------
# StdoutSink
# ---------------------------------------------------------------------------

def test_stdout_sink_writes_json_line():
    buf = io.StringIO()
    sink = StdoutSink(stream=buf)
    sink.write({"level": "info", "msg": "hello"})
    buf.seek(0)
    decoded = json.loads(buf.readline())
    assert decoded["level"] == "info"


def test_stdout_sink_flush_does_not_raise():
    buf = io.StringIO()
    sink = StdoutSink(stream=buf)
    sink.write({"x": 1})
    sink.flush()  # should not raise


def test_stdout_sink_non_serialisable_uses_str_fallback():
    buf = io.StringIO()
    sink = StdoutSink(stream=buf)
    from datetime import datetime
    sink.write({"ts": datetime(2024, 1, 1)})
    buf.seek(0)
    line = buf.readline()
    assert "2024-01-01" in line


# ---------------------------------------------------------------------------
# FileSink
# ---------------------------------------------------------------------------

def test_file_sink_writes_to_file():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
        path = f.name
    try:
        with FileSink(path) as sink:
            sink.write({"msg": "persisted"})
            sink.flush()
        with open(path) as fh:
            data = json.loads(fh.readline())
        assert data["msg"] == "persisted"
    finally:
        os.unlink(path)


def test_file_sink_appends_multiple_events():
    with tempfile.NamedTemporaryFile(mode="r", suffix=".log", delete=False) as f:
        path = f.name
    try:
        with FileSink(path) as sink:
            for i in range(3):
                sink.write({"i": i})
        with open(path) as fh:
            lines = fh.readlines()
        assert len(lines) == 3
    finally:
        os.unlink(path)
