"""Tests for logpipe.enricher."""
from __future__ import annotations

import pytest

from logpipe.enricher import Enricher


# ---------------------------------------------------------------------------
# Construction / configuration
# ---------------------------------------------------------------------------

def test_empty_enricher_returns_copy_of_event():
    e = Enricher()
    event = {"msg": "hello"}
    result = e.enrich(event)
    assert result == event
    assert result is not event  # must be a new dict


def test_add_static_field():
    e = Enricher().add("env", "prod")
    result = e.enrich({"msg": "hi"})
    assert result["env"] == "prod"


def test_add_callable_field():
    e = Enricher().add("upper_msg", lambda ev: ev["msg"].upper())
    result = e.enrich({"msg": "hello"})
    assert result["upper_msg"] == "HELLO"


def test_add_chaining_returns_self():
    e = Enricher()
    returned = e.add("a", 1)
    assert returned is e


def test_add_invalid_key_raises():
    with pytest.raises(ValueError):
        Enricher().add("", "value")


def test_add_non_string_key_raises():
    with pytest.raises(ValueError):
        Enricher().add(123, "value")  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Overwrite behaviour
# ---------------------------------------------------------------------------

def test_overwrite_true_replaces_existing_key():
    e = Enricher().add("env", "prod").overwrite(True)
    result = e.enrich({"env": "dev", "msg": "x"})
    assert result["env"] == "prod"


def test_overwrite_false_preserves_existing_key():
    e = Enricher().add("env", "prod").overwrite(False)
    result = e.enrich({"env": "dev", "msg": "x"})
    assert result["env"] == "dev"


def test_overwrite_false_adds_missing_key():
    e = Enricher().add("env", "prod").overwrite(False)
    result = e.enrich({"msg": "x"})
    assert result["env"] == "prod"


def test_overwrite_returns_self_for_chaining():
    e = Enricher()
    assert e.overwrite(False) is e


# ---------------------------------------------------------------------------
# Multiple fields
# ---------------------------------------------------------------------------

def test_multiple_fields_all_attached():
    e = Enricher().add("a", 1).add("b", 2).add("c", 3)
    result = e.enrich({})
    assert result == {"a": 1, "b": 2, "c": 3}


def test_len_reflects_registered_fields():
    e = Enricher().add("x", 1).add("y", 2)
    assert len(e) == 2


# ---------------------------------------------------------------------------
# Immutability of original event
# ---------------------------------------------------------------------------

def test_original_event_is_not_mutated():
    e = Enricher().add("env", "prod")
    original = {"msg": "hi"}
    e.enrich(original)
    assert "env" not in original
