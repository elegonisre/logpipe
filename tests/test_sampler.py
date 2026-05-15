"""Tests for logpipe.sampler."""
import pytest

from logpipe.sampler import Sampler


# ---------------------------------------------------------------------------
# Construction validation
# ---------------------------------------------------------------------------

def test_invalid_rate_zero_raises():
    with pytest.raises(ValueError, match="rate"):
        Sampler(0.0)


def test_invalid_rate_negative_raises():
    with pytest.raises(ValueError, match="rate"):
        Sampler(-0.5)


def test_invalid_rate_above_one_raises():
    with pytest.raises(ValueError, match="rate"):
        Sampler(1.1)


def test_rate_one_is_valid():
    s = Sampler(1.0)
    assert s.rate == 1.0


# ---------------------------------------------------------------------------
# Counter-based sampling (no key)
# ---------------------------------------------------------------------------

def test_rate_one_keeps_all_events():
    s = Sampler(1.0)
    events = [{"msg": str(i)} for i in range(20)]
    kept = [e for e in events if s.should_keep(e)]
    assert len(kept) == 20


def test_rate_half_keeps_every_other_event():
    s = Sampler(0.5)
    results = [s.should_keep({}) for _ in range(10)]
    kept = sum(results)
    assert kept == 5
    # First event should be kept (counter starts at 0).
    assert results[0] is True
    assert results[1] is False


def test_reset_restarts_counter():
    s = Sampler(0.5)
    s.should_keep({})  # counter -> 1
    s.should_keep({})  # counter -> 2
    s.reset()
    # After reset the first event should again be kept.
    assert s.should_keep({}) is True


def test_rate_one_tenth_keeps_one_in_ten():
    s = Sampler(0.1)
    results = [s.should_keep({}) for _ in range(20)]
    assert results[0] is True
    assert results[1] is False
    assert results[10] is True


# ---------------------------------------------------------------------------
# Hash-based sampling (with key)
# ---------------------------------------------------------------------------

def test_hash_sampling_is_deterministic():
    """Same key value must always produce the same decision."""
    s1 = Sampler(0.5, key="user_id")
    s2 = Sampler(0.5, key="user_id")
    for uid in range(50):
        event = {"user_id": str(uid)}
        assert s1.should_keep(event) == s2.should_keep(event)


def test_hash_sampling_rate_one_keeps_all():
    s = Sampler(1.0, key="id")
    for i in range(30):
        assert s.should_keep({"id": str(i)}) is True


def test_hash_sampling_missing_key_uses_empty_string():
    """Events without the key field should not raise."""
    s = Sampler(0.5, key="user_id")
    # Should not raise regardless of outcome.
    result = s.should_keep({"msg": "no user_id here"})
    assert isinstance(result, bool)


def test_hash_sampling_approximate_rate():
    """With enough samples the kept fraction should be close to the rate."""
    rate = 0.25
    s = Sampler(rate, key="id")
    n = 2000
    kept = sum(1 for i in range(n) if s.should_keep({"id": str(i)}))
    # Allow ±5 percentage points.
    assert abs(kept / n - rate) < 0.05
