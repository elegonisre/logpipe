"""Tests for logpipe.rate_limiter.RateLimiter."""

import time
import pytest

from logpipe.rate_limiter import RateLimiter


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------

def test_invalid_rate_raises():
    with pytest.raises(ValueError, match="rate"):
        RateLimiter(rate=0)


def test_invalid_period_raises():
    with pytest.raises(ValueError, match="period"):
        RateLimiter(rate=10, period=-1)


# ---------------------------------------------------------------------------
# Basic allow / deny behaviour
# ---------------------------------------------------------------------------

def test_allows_up_to_rate_events():
    rl = RateLimiter(rate=5)
    allowed = sum(1 for _ in range(5) if rl.allow())
    assert allowed == 5


def test_denies_events_beyond_rate():
    rl = RateLimiter(rate=3)
    results = [rl.allow() for _ in range(6)]
    assert results[:3] == [True, True, True]
    assert results[3:] == [False, False, False]


def test_single_event_always_allowed_on_fresh_limiter():
    rl = RateLimiter(rate=1)
    assert rl.allow() is True


# ---------------------------------------------------------------------------
# Token replenishment
# ---------------------------------------------------------------------------

def test_tokens_replenish_over_time():
    rl = RateLimiter(rate=10, period=0.1)
    # Drain the bucket
    for _ in range(10):
        rl.allow()
    assert rl.allow() is False

    # Wait for a full replenishment window
    time.sleep(0.15)
    assert rl.allow() is True


def test_tokens_do_not_exceed_rate():
    rl = RateLimiter(rate=5, period=0.05)
    time.sleep(0.3)  # Let several windows pass
    assert rl.tokens <= 5.0


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------

def test_reset_refills_bucket():
    rl = RateLimiter(rate=3)
    for _ in range(3):
        rl.allow()
    assert rl.allow() is False
    rl.reset()
    assert rl.allow() is True


def test_reset_fills_to_full_rate():
    rl = RateLimiter(rate=7)
    for _ in range(7):
        rl.allow()
    rl.reset()
    allowed = sum(1 for _ in range(7) if rl.allow())
    assert allowed == 7


# ---------------------------------------------------------------------------
# tokens property
# ---------------------------------------------------------------------------

def test_tokens_decreases_after_allow():
    rl = RateLimiter(rate=10)
    before = rl.tokens
    rl.allow()
    assert rl.tokens < before


def test_tokens_starts_at_rate():
    rl = RateLimiter(rate=4)
    assert rl.tokens == pytest.approx(4.0, abs=0.01)
