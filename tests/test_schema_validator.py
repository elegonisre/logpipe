"""Tests for logpipe.schema_validator."""
import pytest

from logpipe.schema_validator import SchemaValidator


# ---------------------------------------------------------------------------
# require()
# ---------------------------------------------------------------------------

def test_valid_event_passes():
    v = SchemaValidator().require("level", str).require("ts", (int, float))
    ok, errors = v.validate({"level": "info", "ts": 1234567890})
    assert ok
    assert errors == []


def test_missing_required_field_fails():
    v = SchemaValidator().require("level")
    ok, errors = v.validate({})
    assert not ok
    assert any("level" in e for e in errors)


def test_required_field_wrong_type_fails():
    v = SchemaValidator().require("level", str)
    ok, errors = v.validate({"level": 42})
    assert not ok
    assert any("level" in e for e in errors)


def test_required_field_no_check_allows_any_type():
    v = SchemaValidator().require("payload")
    ok, _ = v.validate({"payload": [1, 2, 3]})
    assert ok


# ---------------------------------------------------------------------------
# optional()
# ---------------------------------------------------------------------------

def test_optional_field_absent_is_valid():
    v = SchemaValidator().optional("host", str)
    ok, errors = v.validate({})
    assert ok
    assert errors == []


def test_optional_field_present_valid_type():
    v = SchemaValidator().optional("host", str)
    ok, _ = v.validate({"host": "web-01"})
    assert ok


def test_optional_field_present_wrong_type_fails():
    v = SchemaValidator().optional("host", str)
    ok, errors = v.validate({"host": 99})
    assert not ok
    assert any("host" in e for e in errors)


# ---------------------------------------------------------------------------
# callable predicate
# ---------------------------------------------------------------------------

def test_callable_predicate_passes():
    v = SchemaValidator().require("count", lambda x: isinstance(x, int) and x > 0)
    ok, _ = v.validate({"count": 5})
    assert ok


def test_callable_predicate_fails():
    v = SchemaValidator().require("count", lambda x: isinstance(x, int) and x > 0)
    ok, errors = v.validate({"count": -1})
    assert not ok
    assert any("count" in e for e in errors)


# ---------------------------------------------------------------------------
# is_valid convenience method
# ---------------------------------------------------------------------------

def test_is_valid_returns_bool():
    v = SchemaValidator().require("msg", str)
    assert v.is_valid({"msg": "hello"}) is True
    assert v.is_valid({"msg": 0}) is False


# ---------------------------------------------------------------------------
# chaining & invalid check argument
# ---------------------------------------------------------------------------

def test_chaining_returns_self():
    v = SchemaValidator()
    assert v.require("a") is v
    assert v.optional("b") is v


def test_invalid_check_type_raises():
    with pytest.raises(TypeError):
        SchemaValidator().require("field", 123)


# ---------------------------------------------------------------------------
# multiple errors reported together
# ---------------------------------------------------------------------------

def test_multiple_errors_reported():
    v = SchemaValidator().require("a", str).require("b", int)
    ok, errors = v.validate({"a": 1, "b": "wrong"})
    assert not ok
    assert len(errors) == 2
