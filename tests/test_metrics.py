"""Tests for logpipe.metrics."""
import threading
import time

import pytest

from logpipe.metrics import Metrics


@pytest.fixture()
def m() -> Metrics:
    return Metrics()


def test_counter_starts_at_zero(m: Metrics) -> None:
    assert m.counter("lines_read") == 0


def test_increment_increases_counter(m: Metrics) -> None:
    m.increment("lines_read")
    m.increment("lines_read")
    assert m.counter("lines_read") == 2


def test_increment_by_custom_amount(m: Metrics) -> None:
    m.increment("bytes", 512)
    assert m.counter("bytes") == 512


def test_multiple_counters_are_independent(m: Metrics) -> None:
    m.increment("a")
    m.increment("b", 3)
    assert m.counter("a") == 1
    assert m.counter("b") == 3


def test_gauge_defaults_to_zero(m: Metrics) -> None:
    assert m.gauge("queue_depth") == 0.0


def test_set_gauge_stores_value(m: Metrics) -> None:
    m.set_gauge("queue_depth", 42.5)
    assert m.gauge("queue_depth") == 42.5


def test_snapshot_contains_all_sections(m: Metrics) -> None:
    m.increment("events")
    m.set_gauge("lag", 1.2)
    snap = m.snapshot()
    assert "uptime_seconds" in snap
    assert snap["counters"]["events"] == 1
    assert snap["gauges"]["lag"] == 1.2


def test_snapshot_is_a_copy(m: Metrics) -> None:
    snap = m.snapshot()
    snap["counters"]["x"] = 99
    assert m.counter("x") == 0


def test_reset_clears_counters_and_gauges(m: Metrics) -> None:
    m.increment("lines_read", 10)
    m.set_gauge("lag", 5.0)
    m.reset()
    assert m.counter("lines_read") == 0
    assert m.gauge("lag") == 0.0


def test_uptime_increases_over_time(m: Metrics) -> None:
    time.sleep(0.05)
    assert m.snapshot()["uptime_seconds"] >= 0.04


def test_thread_safety(m: Metrics) -> None:
    """Many threads incrementing the same counter must not lose updates."""
    threads = [
        threading.Thread(target=lambda: m.increment("hits", 1))
        for _ in range(200)
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert m.counter("hits") == 200
