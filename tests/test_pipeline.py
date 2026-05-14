"""Tests for logpipe.pipeline (including filter integration)."""

import json
import os
import tempfile
import time

import pytest

from logpipe.filter import Filter, field_equals, min_level
from logpipe.pipeline import Pipeline
from logpipe.sink import MemorySink


def _write(path: str, *lines: str) -> None:
    with open(path, "a") as fh:
        for line in lines:
            fh.write(line + "\n")


def test_pipeline_parses_json_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        _write(path, json.dumps({"level": "info", "msg": "hello"}))
        sink = MemorySink()
        p = Pipeline([path], sink)
        p.run_once()
        assert sink.events[0]["msg"] == "hello"
    finally:
        os.unlink(path)


def test_pipeline_parses_logfmt_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        _write(path, 'level=info msg=world')
        sink = MemorySink()
        p = Pipeline([path], sink)
        p.run_once()
        assert sink.events[0]["msg"] == "world"
    finally:
        os.unlink(path)


def test_pipeline_merges_extra_fields():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        _write(path, json.dumps({"msg": "hi"}))
        sink = MemorySink()
        p = Pipeline([path], sink, extra_fields={"host": "box1"})
        p.run_once()
        assert sink.events[0]["host"] == "box1"
    finally:
        os.unlink(path)


def test_pipeline_skips_unparseable_lines():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        _write(path, "not parseable at all!!!")
        sink = MemorySink()
        p = Pipeline([path], sink)
        p.run_once()
        assert sink.events == []
    finally:
        os.unlink(path)


def test_pipeline_filter_drops_non_matching_events():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        _write(
            path,
            json.dumps({"level": "info", "msg": "keep"}),
            json.dumps({"level": "debug", "msg": "drop"}),
        )
        sink = MemorySink()
        f_obj = Filter([field_equals("level", "info")])
        p = Pipeline([path], sink, event_filter=f_obj)
        p.run_once()
        assert len(sink.events) == 1
        assert sink.events[0]["msg"] == "keep"
    finally:
        os.unlink(path)


def test_pipeline_set_filter_replaces_filter():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
        path = f.name
    try:
        _write(path, json.dumps({"level": "error", "msg": "boom"}))
        sink = MemorySink()
        p = Pipeline([path], sink, event_filter=Filter([field_equals("level", "info")]))
        p.run_once()  # filtered out
        assert sink.events == []

        # Replace with permissive filter
        p.set_filter(Filter())
        _write(path, json.dumps({"level": "error", "msg": "boom2"}))
        p.run_once()
        assert len(sink.events) == 1
    finally:
        os.unlink(path)
