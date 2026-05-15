"""Tests for InstrumentedPipeline metrics integration."""
import json
import os
import tempfile
from pathlib import Path

import pytest

from logpipe.metrics import Metrics
from logpipe.instrumented_pipeline import InstrumentedPipeline
from logpipe.sink import MemorySink
from logpipe.filter import Filter


def _write(path: str, lines: list) -> None:
    with open(path, "a") as fh:
        for line in lines:
            fh.write(line + "\n")


@pytest.fixture()
def tmp_log(tmp_path: Path):
    return str(tmp_path / "app.log")


@pytest.fixture()
def metrics() -> Metrics:
    m = Metrics()
    return m


def test_lines_read_counter(tmp_log, metrics):
    _write(tmp_log, [json.dumps({"msg": "a"}), json.dumps({"msg": "b"})])
    sink = MemorySink()
    p = InstrumentedPipeline([tmp_log], sink, metrics=metrics)
    p.run_once()
    assert metrics.counter("lines_read") == 2


def test_events_parsed_counter(tmp_log, metrics):
    _write(tmp_log, [json.dumps({"msg": "ok"}), "not parseable garbage"])
    sink = MemorySink()
    p = InstrumentedPipeline([tmp_log], sink, metrics=metrics)
    p.run_once()
    assert metrics.counter("events_parsed") == 1
    assert metrics.counter("parse_errors") == 1


def test_events_forwarded_counter(tmp_log, metrics):
    _write(tmp_log, [json.dumps({"level": "info", "msg": "hi"})])
    sink = MemorySink()
    p = InstrumentedPipeline([tmp_log], sink, metrics=metrics)
    count = p.run_once()
    assert count == 1
    assert metrics.counter("events_forwarded") == 1


def test_events_dropped_counter(tmp_log, metrics):
    _write(tmp_log, [json.dumps({"level": "debug", "msg": "verbose"})])
    sink = MemorySink()
    p = InstrumentedPipeline([tmp_log], sink, metrics=metrics)
    f = Filter()
    from logpipe.filter import has_field_value
    f.add(has_field_value("level", "error"))
    p.set_filter(f)
    p.run_once()
    assert metrics.counter("events_dropped") == 1
    assert metrics.counter("events_forwarded") == 0


def test_last_run_forwarded_gauge(tmp_log, metrics):
    _write(tmp_log, [json.dumps({"msg": "x"})] * 3)
    sink = MemorySink()
    p = InstrumentedPipeline([tmp_log], sink, metrics=metrics)
    p.run_once()
    assert metrics.gauge("last_run_forwarded") == 3.0


def test_uses_default_metrics_when_none_given(tmp_log):
    from logpipe.metrics import default_metrics
    default_metrics.reset()
    _write(tmp_log, [json.dumps({"msg": "hi"})])
    sink = MemorySink()
    p = InstrumentedPipeline([tmp_log], sink)
    p.run_once()
    assert default_metrics.counter("lines_read") >= 1
