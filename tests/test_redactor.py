"""Tests for logpipe.redactor."""

import pytest

from logpipe.redactor import Redactor


# ---------------------------------------------------------------------------
# Construction / validation
# ---------------------------------------------------------------------------

def test_unknown_mask_string_raises():
    r = Redactor()
    with pytest.raises(ValueError, match="Unknown mask"):
        r.add("field", mask="invisible")


def test_add_returns_self_for_chaining():
    r = Redactor()
    assert r.add("x") is r


def test_add_pattern_returns_self_for_chaining():
    r = Redactor()
    assert r.add_pattern(r"secret_.*") is r


# ---------------------------------------------------------------------------
# Full mask (default)
# ---------------------------------------------------------------------------

def test_full_mask_replaces_value():
    r = Redactor().add("password")
    result = r.redact({"user": "alice", "password": "s3cr3t"})
    assert result["password"] == "***"
    assert result["user"] == "alice"


def test_redact_returns_new_dict():
    event = {"password": "abc"}
    r = Redactor().add("password")
    result = r.redact(event)
    assert result is not event


def test_non_string_values_are_left_untouched():
    r = Redactor().add("count")
    result = r.redact({"count": 42})
    assert result["count"] == 42


# ---------------------------------------------------------------------------
# Partial mask
# ---------------------------------------------------------------------------

def test_partial_mask_keeps_first_two_chars():
    r = Redactor().add("token", mask="partial")
    result = r.redact({"token": "abcdef"})
    assert result["token"] == "ab***"


def test_partial_mask_short_value():
    r = Redactor().add("token", mask="partial")
    result = r.redact({"token": "x"})
    assert result["token"] == "***"


# ---------------------------------------------------------------------------
# Hash mask
# ---------------------------------------------------------------------------

def test_hash_mask_starts_with_hash_symbol():
    r = Redactor().add("api_key", mask="hash")
    result = r.redact({"api_key": "supersecret"})
    assert result["api_key"].startswith("#")


def test_hash_mask_is_deterministic():
    r = Redactor().add("api_key", mask="hash")
    e = {"api_key": "supersecret"}
    assert r.redact(e)["api_key"] == r.redact(e)["api_key"]


# ---------------------------------------------------------------------------
# Custom callable mask
# ---------------------------------------------------------------------------

def test_custom_callable_mask():
    r = Redactor().add("ssn", mask=lambda v: "XXX-XX-" + v[-4:])
    result = r.redact({"ssn": "123-45-6789"})
    assert result["ssn"] == "XXX-XX-6789"


# ---------------------------------------------------------------------------
# Pattern-based redaction
# ---------------------------------------------------------------------------

def test_pattern_matches_field():
    r = Redactor().add_pattern(r"secret_.*")
    result = r.redact({"secret_key": "abc", "public": "ok"})
    assert result["secret_key"] == "***"
    assert result["public"] == "ok"


def test_pattern_does_not_match_partial_name():
    r = Redactor().add_pattern(r"secret_.*")
    result = r.redact({"my_secret_key": "abc"})
    # fullmatch — prefix doesn't match
    assert result["my_secret_key"] == "abc"


def test_exact_field_takes_precedence_over_pattern():
    custom = lambda v: "CUSTOM"
    r = Redactor().add_pattern(r"token").add("token", mask=custom)
    result = r.redact({"token": "xyz"})
    assert result["token"] == "CUSTOM"


def test_empty_redactor_is_identity():
    r = Redactor()
    event = {"msg": "hello", "level": "info"}
    assert r.redact(event) == event
