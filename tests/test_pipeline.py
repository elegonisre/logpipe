"""Tests for logpipe.pipeline.Pipeline."""

from __future__ import annotations

import json
import os
import tempfile
import threading
import time

import pytest

from logpipe.pipeline import Pipeline
from logpipe.sink import MemorySink


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _write(path: str, lines: list[str]) -> None:
    with open(path, "a") as fh:
        for line in lines:
            fh.write(line + "\n")
        fh.flush()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_pipeline_parses_json_lines(tmp_path):
    log_file = tmp_path / "app.log"
    events = [{"level": "info", "msg": "hello"}, {"level": "error", "msg": "boom"}]
    _write(str(log_file), [json.dumps(e) for e in events])

    sink = MemorySink()
    pipeline = Pipeline(str(log_file), sink)
    count = pipeline.run_once()

    assert count == 2
    assert sink.events[0]["msg"] == "hello"
    assert sink.events[1]["level"] == "error"


def test_pipeline_parses_logfmt_lines(tmp_path):
    log_file = tmp_path / "app.log"
    _write(str(log_file), ['level=info msg=started ts=2024-01-01'])

    sink = MemorySink()
    pipeline = Pipeline(str(log_file), sink)
    pipeline.run_once()

    assert sink.events[0]["level"] == "info"
    assert sink.events[0]["msg"] == "started"


def test_pipeline_merges_extra_fields(tmp_path):
    log_file = tmp_path / "app.log"
    _write(str(log_file), [json.dumps({"msg": "ok"})])

    sink = MemorySink()
    pipeline = Pipeline(str(log_file), sink, extra={"host": "web-01", "env": "prod"})
    pipeline.run_once()

    assert sink.events[0]["host"] == "web-01"
    assert sink.events[0]["env"] == "prod"
    assert sink.events[0]["msg"] == "ok"


def test_pipeline_skips_unparseable_lines(tmp_path):
    log_file = tmp_path / "app.log"
    _write(str(log_file), ["plain text line", json.dumps({"ok": True})])

    sink = MemorySink()
    pipeline = Pipeline(str(log_file), sink)
    count = pipeline.run_once()

    assert count == 1
    assert sink.events[0]["ok"] is True


def test_pipeline_start_stop(tmp_path):
    log_file = tmp_path / "app.log"
    log_file.write_text("")  # create empty file

    sink = MemorySink()
    pipeline = Pipeline(str(log_file), sink, poll_interval=0.05)
    pipeline.start()

    _write(str(log_file), [json.dumps({"seq": i}) for i in range(5)])
    time.sleep(0.4)

    pipeline.stop(timeout=2.0)

    assert len(sink.events) == 5
    assert [e["seq"] for e in sink.events] == list(range(5))
