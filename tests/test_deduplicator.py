"""Tests for logpipe.deduplicator."""

from __future__ import annotations

import time

import pytest

from logpipe.deduplicator import Deduplicator, _event_hash


# ---------------------------------------------------------------------------
# _event_hash
# ---------------------------------------------------------------------------

def test_hash_is_stable_across_key_order():
    a = _event_hash({"level": "info", "msg": "hello"})
    b = _event_hash({"msg": "hello", "level": "info"})
    assert a == b


def test_different_events_produce_different_hashes():
    a = _event_hash({"msg": "hello"})
    b = _event_hash({"msg": "world"})
    assert a != b


# ---------------------------------------------------------------------------
# Deduplicator construction
# ---------------------------------------------------------------------------

def test_invalid_window_raises():
    with pytest.raises(ValueError, match="window_seconds"):
        Deduplicator(window_seconds=0)


def test_invalid_max_size_raises():
    with pytest.raises(ValueError, match="max_size"):
        Deduplicator(max_size=0)


# ---------------------------------------------------------------------------
# is_duplicate
# ---------------------------------------------------------------------------

def test_first_occurrence_is_not_duplicate():
    d = Deduplicator()
    assert d.is_duplicate({"msg": "hello"}) is False


def test_second_occurrence_within_window_is_duplicate():
    d = Deduplicator(window_seconds=60)
    event = {"msg": "hello", "level": "info"}
    d.is_duplicate(event)
    assert d.is_duplicate(event) is True


def test_different_event_not_duplicate():
    d = Deduplicator()
    d.is_duplicate({"msg": "hello"})
    assert d.is_duplicate({"msg": "world"}) is False


def test_event_allowed_again_after_window_expires(monkeypatch):
    d = Deduplicator(window_seconds=1)
    event = {"msg": "hello"}

    base = time.monotonic()
    monkeypatch.setattr("logpipe.deduplicator.time.monotonic", lambda: base)
    d.is_duplicate(event)  # record

    # Advance time beyond the window.
    monkeypatch.setattr("logpipe.deduplicator.time.monotonic", lambda: base + 2)
    assert d.is_duplicate(event) is False


# ---------------------------------------------------------------------------
# size / eviction
# ---------------------------------------------------------------------------

def test_size_tracks_unique_events():
    d = Deduplicator()
    d.is_duplicate({"msg": "a"})
    d.is_duplicate({"msg": "b"})
    d.is_duplicate({"msg": "a"})  # duplicate — should not grow size
    assert d.size == 2


def test_max_size_evicts_oldest():
    d = Deduplicator(max_size=3)
    for i in range(3):
        d.is_duplicate({"id": i})
    assert d.size == 3
    # Adding a 4th unique event should evict the oldest.
    d.is_duplicate({"id": 99})
    assert d.size == 3


# ---------------------------------------------------------------------------
# reset
# ---------------------------------------------------------------------------

def test_reset_clears_all_hashes():
    d = Deduplicator()
    event = {"msg": "hello"}
    d.is_duplicate(event)
    d.reset()
    assert d.size == 0
    assert d.is_duplicate(event) is False  # treated as new
