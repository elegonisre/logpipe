"""Tests for logpipe.filter."""

import pytest
from logpipe.filter import (
    Filter,
    field_contains,
    field_equals,
    has_field,
    min_level,
)


# ---------------------------------------------------------------------------
# Filter class
# ---------------------------------------------------------------------------

def test_empty_filter_accepts_everything():
    f = Filter()
    assert f.match({"msg": "hello"}) is True


def test_filter_apply_returns_matching_subset():
    f = Filter([has_field("level")])
    events = [{"level": "info", "msg": "a"}, {"msg": "b"}]
    assert f.apply(events) == [{"level": "info", "msg": "a"}]


def test_filter_all_predicates_must_pass():
    f = Filter([has_field("level"), field_equals("level", "error")])
    assert f.match({"level": "info"}) is False
    assert f.match({"level": "error"}) is True


def test_filter_add_chaining():
    f = Filter()
    returned = f.add(has_field("msg"))
    assert returned is f  # fluent interface
    assert f.match({"msg": "hi"}) is True
    assert f.match({}) is False


# ---------------------------------------------------------------------------
# has_field
# ---------------------------------------------------------------------------

def test_has_field_present():
    assert has_field("x")({"x": 1}) is True


def test_has_field_absent():
    assert has_field("x")({"y": 1}) is False


# ---------------------------------------------------------------------------
# field_equals
# ---------------------------------------------------------------------------

def test_field_equals_match():
    assert field_equals("env", "prod")({"env": "prod"}) is True


def test_field_equals_no_match():
    assert field_equals("env", "prod")({"env": "dev"}) is False


def test_field_equals_missing_key():
    assert field_equals("env", "prod")({}) is False


# ---------------------------------------------------------------------------
# field_contains
# ---------------------------------------------------------------------------

def test_field_contains_match():
    assert field_contains("msg", "error")({"msg": "an error occurred"}) is True


def test_field_contains_no_match():
    assert field_contains("msg", "error")({"msg": "all good"}) is False


# ---------------------------------------------------------------------------
# min_level
# ---------------------------------------------------------------------------

def test_min_level_exact_match():
    assert min_level("warning")({"level": "warning"}) is True


def test_min_level_above_threshold():
    assert min_level("warning")({"level": "error"}) is True


def test_min_level_below_threshold():
    assert min_level("warning")({"level": "info"}) is False


def test_min_level_unknown_level_in_event():
    assert min_level("info")({"level": "verbose"}) is False


def test_min_level_missing_level_key():
    assert min_level("info")({"msg": "hello"}) is False
