"""Tests for logpipe.transformer."""
import pytest

from logpipe.transformer import Transformer


# ---------------------------------------------------------------------------
# add / chaining
# ---------------------------------------------------------------------------

def test_add_non_callable_raises():
    t = Transformer()
    with pytest.raises(TypeError):
        t.add("not_a_function")  # type: ignore[arg-type]


def test_add_returns_self_for_chaining():
    t = Transformer()
    assert t.add(lambda e: e) is t


# ---------------------------------------------------------------------------
# apply — identity / empty pipeline
# ---------------------------------------------------------------------------

def test_empty_transformer_returns_copy_of_event():
    t = Transformer()
    event = {"msg": "hello", "level": "info"}
    result = t.apply(event)
    assert result == event
    assert result is not event  # must be a copy


# ---------------------------------------------------------------------------
# built-in helpers
# ---------------------------------------------------------------------------

def test_rename_existing_key():
    t = Transformer().rename("msg", "message")
    result = t.apply({"msg": "hi", "level": "info"})
    assert "message" in result
    assert "msg" not in result
    assert result["message"] == "hi"


def test_rename_missing_key_is_noop():
    t = Transformer().rename("missing", "other")
    event = {"level": "warn"}
    assert t.apply(event) == {"level": "warn"}


def test_drop_field_removes_key():
    t = Transformer().drop_field("password")
    result = t.apply({"user": "alice", "password": "secret"})
    assert "password" not in result
    assert result["user"] == "alice"


def test_drop_field_missing_key_is_noop():
    t = Transformer().drop_field("ghost")
    event = {"level": "debug"}
    assert t.apply(event) == {"level": "debug"}


def test_add_field_sets_value():
    t = Transformer().add_field("env", "production")
    result = t.apply({"msg": "ok"})
    assert result["env"] == "production"


def test_add_field_overwrites_existing():
    t = Transformer().add_field("env", "staging")
    result = t.apply({"env": "dev", "msg": "ok"})
    assert result["env"] == "staging"


def test_mask_field_replaces_value():
    t = Transformer().mask_field("token")
    result = t.apply({"token": "abc123", "user": "bob"})
    assert result["token"] == "***"


def test_mask_field_custom_mask():
    t = Transformer().mask_field("ssn", mask="[REDACTED]")
    result = t.apply({"ssn": "123-45-6789"})
    assert result["ssn"] == "[REDACTED]"


def test_mask_field_missing_key_is_noop():
    t = Transformer().mask_field("secret")
    event = {"msg": "safe"}
    assert t.apply(event) == {"msg": "safe"}


# ---------------------------------------------------------------------------
# drop via custom step returning None
# ---------------------------------------------------------------------------

def test_step_returning_none_drops_event():
    t = Transformer().add(lambda e: None)
    assert t.apply({"msg": "bye"}) is None


def test_steps_after_none_are_skipped():
    called = []
    def _spy(e):
        called.append(e)
        return e

    t = Transformer().add(lambda e: None).add(_spy)
    assert t.apply({"x": 1}) is None
    assert called == []


# ---------------------------------------------------------------------------
# chained mutations
# ---------------------------------------------------------------------------

def test_multiple_steps_applied_in_order():
    t = (
        Transformer()
        .rename("msg", "message")
        .add_field("env", "test")
        .drop_field("debug")
    )
    result = t.apply({"msg": "hello", "debug": True})
    assert result == {"message": "hello", "env": "test"}


def test_original_event_is_not_mutated():
    t = Transformer().add_field("injected", 42)
    original = {"msg": "unchanged"}
    t.apply(original)
    assert "injected" not in original
