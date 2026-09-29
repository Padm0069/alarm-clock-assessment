from datetime import datetime, timedelta

from alarm.runner import run_loop
from alarm.store import Store


class FakeTime:
    def __init__(self, start):
        self.now = start

    def clock(self):
        return self.now

    def sleep(self, seconds):
        self.now += timedelta(seconds=seconds)


def make(tmp_path, start):
    return Store(tmp_path / "a.json"), FakeTime(start)


def test_once_alarm_rings_exactly_once_then_disables(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 50))
    store.add("07:30", "wake")
    rings = []
    run_loop(store, t.clock, t.sleep, lambda al, now: rings.append((now, [a.label for a in al])) or "dismiss",
             max_ticks=180)
    assert rings == [(datetime(2026, 10, 1, 7, 30, 0), ["wake"])]
    assert store.load()[0].enabled is False


def test_alarm_for_past_time_does_not_ring_today(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 31, 0))
    store.add("07:30")
    rings = []
    run_loop(store, t.clock, t.sleep, lambda al, now: rings.append(now) or "dismiss", max_ticks=300)
    assert rings == []


def test_daily_alarm_rings_once_per_minute_not_sixty_times(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 50))
    store.add("07:30", repeat="daily")
    rings = []
    run_loop(store, t.clock, t.sleep, lambda al, now: rings.append(now) or "dismiss", max_ticks=120)
    assert len(rings) == 1
    assert store.load()[0].enabled is True


def test_snooze_rings_again_after_snooze_period(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 59))
    store.add("07:30")
    answers = iter(["snooze", "dismiss"])
    rings = []
    run_loop(store, t.clock, t.sleep,
             lambda al, now: rings.append(now) or next(answers),
             snooze_minutes=5, max_ticks=400)
    assert rings == [datetime(2026, 10, 1, 7, 30, 0), datetime(2026, 10, 1, 7, 35, 0)]


def test_alarm_that_comes_due_while_ringing_is_not_lost(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 59))
    store.add("07:30", "A")
    store.add("07:31", "B")
    rings = []

    def slow_ring(alarms, now):             # user takes 2 minutes to react
        rings.append([a.label for a in alarms])
        t.now += timedelta(minutes=2)
        return "dismiss"

    run_loop(store, t.clock, t.sleep, slow_ring, max_ticks=5)
    assert rings == [["A"], ["B"]]


def test_two_alarms_same_minute_ring_together(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 59))
    store.add("07:30", "A")
    store.add("07:30", "B")
    rings = []
    run_loop(store, t.clock, t.sleep, lambda al, now: rings.append([a.label for a in al]) or "dismiss",
             max_ticks=5)
    assert rings == [["A", "B"]]


def test_alarm_added_while_running_is_picked_up(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 0))
    rings = []
    ticks = {"n": 0}

    def sleep(s):
        ticks["n"] += 1
        if ticks["n"] == 10:                # "another terminal" adds an alarm
            store.add("07:30", "late add")
        t.sleep(s)

    run_loop(store, t.clock, sleep, lambda al, now: rings.append(al[0].label) or "dismiss", max_ticks=90)
    assert rings == ["late add"]
