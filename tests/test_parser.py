"""Tests for logpipe.parser."""

import json

import pytest

from logpipe.parser import parse_json, parse_line, parse_logfmt


# ---------------------------------------------------------------------------
# parse_json
# ---------------------------------------------------------------------------

def test_parse_json_valid_object():
    line = json.dumps({"level": "info", "msg": "hello"})
    result = parse_json(line)
    assert result == {"level": "info", "msg": "hello"}


def test_parse_json_returns_none_for_plain_text():
    assert parse_json("not json at all") is None


def test_parse_json_returns_none_for_json_array():
    assert parse_json("[1, 2, 3]") is None


# ---------------------------------------------------------------------------
# parse_logfmt
# ---------------------------------------------------------------------------

def test_parse_logfmt_basic():
    result = parse_logfmt('level=info msg="user logged in" user=alice')
    assert result == {"level": "info", "msg": "user logged in", "user": "alice"}


def test_parse_logfmt_no_pairs_returns_none():
    assert parse_logfmt("just a plain sentence") is None


def test_parse_logfmt_unquoted_values():
    result = parse_logfmt("status=200 path=/health")
    assert result["status"] == "200"
    assert result["path"] == "/health"


# ---------------------------------------------------------------------------
# parse_line — integration
# ---------------------------------------------------------------------------

def test_parse_line_json_preferred():
    line = json.dumps({"level": "warn", "msg": "disk full"})
    event = parse_line(line, source="app.log")
    assert event["level"] == "warn"
    assert event["_source"] == "app.log"
    assert "_ts" in event


def test_parse_line_fallback_to_logfmt():
    event = parse_line("level=debug msg=starting", source="svc.log")
    assert event["level"] == "debug"
    assert event["_source"] == "svc.log"


def test_parse_line_fallback_to_plain_text():
    event = parse_line("something went wrong", source="err.log")
    assert event["message"] == "something went wrong"
    assert event["_source"] == "err.log"


def test_parse_line_strips_newline():
    event = parse_line("plain text\n", source="x")
    assert event["message"] == "plain text"


def test_parse_line_does_not_overwrite_existing_source():
    line = json.dumps({"_source": "original", "msg": "hi"})
    event = parse_line(line, source="injected")
    assert event["_source"] == "original"
