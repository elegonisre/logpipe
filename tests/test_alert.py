"""Tests for logpipe.alert."""
import pytest
from logpipe.alert import AlertManager, AlertRule


# ---------------------------------------------------------------------------
# AlertRule construction
# ---------------------------------------------------------------------------

def test_invalid_comparator_raises():
    with pytest.raises(ValueError, match="Unknown comparator"):
        AlertRule(name="r", metric="m", threshold=1.0, comparator="bad", message="x")


def test_negative_cooldown_raises():
    with pytest.raises(ValueError, match="cooldown"):
        AlertRule(name="r", metric="m", threshold=1.0, comparator="gt", message="x", cooldown=-1)


def test_evaluate_gt_true():
    rule = AlertRule(name="r", metric="m", threshold=5.0, comparator="gt", message="hi")
    assert rule.evaluate(6.0) is True


def test_evaluate_gt_false():
    rule = AlertRule(name="r", metric="m", threshold=5.0, comparator="gt", message="hi")
    assert rule.evaluate(5.0) is False


def test_evaluate_lt():
    rule = AlertRule(name="r", metric="m", threshold=3.0, comparator="lt", message="low")
    assert rule.evaluate(2.0) is True
    assert rule.evaluate(3.0) is False


def test_evaluate_gte():
    rule = AlertRule(name="r", metric="m", threshold=3.0, comparator="gte", message="x")
    assert rule.evaluate(3.0) is True


def test_evaluate_lte():
    rule = AlertRule(name="r", metric="m", threshold=3.0, comparator="lte", message="x")
    assert rule.evaluate(3.0) is True


def test_evaluate_eq():
    rule = AlertRule(name="r", metric="m", threshold=7.0, comparator="eq", message="x")
    assert rule.evaluate(7.0) is True
    assert rule.evaluate(8.0) is False


# ---------------------------------------------------------------------------
# AlertManager
# ---------------------------------------------------------------------------

def _make_clock(start: float = 0.0):
    """Returns a mutable clock list [value] and a callable."""
    t = [start]
    return t, lambda: t[0]


def test_no_rules_fires_nothing():
    mgr = AlertManager()
    assert mgr.evaluate({"errors": 100}) == 0


def test_matching_rule_fires_handler():
    t, clock = _make_clock()
    mgr = AlertManager(clock=clock)
    rule = AlertRule(name="high_errors", metric="errors", threshold=10, comparator="gt", message="too many errors")
    mgr.add_rule(rule)

    fired = []
    mgr.on_alert(lambda r, v: fired.append((r.name, v)))

    count = mgr.evaluate({"errors": 15})
    assert count == 1
    assert fired == [("high_errors", 15)]


def test_non_matching_rule_does_not_fire():
    t, clock = _make_clock()
    mgr = AlertManager(clock=clock)
    rule = AlertRule(name="r", metric="errors", threshold=10, comparator="gt", message="x")
    mgr.add_rule(rule)
    assert mgr.evaluate({"errors": 5}) == 0


def test_missing_metric_is_skipped():
    mgr = AlertManager()
    rule = AlertRule(name="r", metric="missing", threshold=1, comparator="gt", message="x")
    mgr.add_rule(rule)
    assert mgr.evaluate({"other": 99}) == 0


def test_cooldown_suppresses_repeated_alert():
    t, clock = _make_clock(0.0)
    mgr = AlertManager(clock=clock)
    rule = AlertRule(name="r", metric="cpu", threshold=80, comparator="gt", message="hot", cooldown=30.0)
    mgr.add_rule(rule)

    fired = []
    mgr.on_alert(lambda r, v: fired.append(v))

    mgr.evaluate({"cpu": 90})   # fires
    t[0] = 10.0
    mgr.evaluate({"cpu": 90})   # suppressed (within cooldown)
    assert len(fired) == 1


def test_cooldown_allows_after_period():
    t, clock = _make_clock(0.0)
    mgr = AlertManager(clock=clock)
    rule = AlertRule(name="r", metric="cpu", threshold=80, comparator="gt", message="hot", cooldown=30.0)
    mgr.add_rule(rule)

    fired = []
    mgr.on_alert(lambda r, v: fired.append(v))

    mgr.evaluate({"cpu": 90})   # fires at t=0
    t[0] = 31.0
    mgr.evaluate({"cpu": 90})   # fires again after cooldown
    assert len(fired) == 2


def test_fire_count_tracks_alerts():
    t, clock = _make_clock(0.0)
    mgr = AlertManager(clock=clock)
    rule = AlertRule(name="r", metric="m", threshold=1, comparator="gt", message="x", cooldown=0.0)
    mgr.add_rule(rule)

    mgr.evaluate({"m": 5})
    t[0] = 1.0
    mgr.evaluate({"m": 5})
    assert mgr.fire_count("r") == 2


def test_reset_clears_state():
    t, clock = _make_clock(0.0)
    mgr = AlertManager(clock=clock)
    rule = AlertRule(name="r", metric="m", threshold=1, comparator="gt", message="x", cooldown=60.0)
    mgr.add_rule(rule)

    mgr.evaluate({"m": 5})
    mgr.reset()
    assert mgr.fire_count("r") == 0
    # should fire again after reset even within original cooldown window
    fired = []
    mgr.on_alert(lambda r, v: fired.append(v))
    mgr.evaluate({"m": 5})
    assert len(fired) == 1


def test_add_rule_chaining():
    mgr = AlertManager()
    rule = AlertRule(name="r", metric="m", threshold=1, comparator="gt", message="x")
    result = mgr.add_rule(rule)
    assert result is mgr


def test_on_alert_chaining():
    mgr = AlertManager()
    result = mgr.on_alert(lambda r, v: None)
    assert result is mgr
