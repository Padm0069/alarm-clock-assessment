from datetime import datetime, timedelta

from alarm.models import Alarm, due_alarms, fmt_delta, next_fire


def A(id, t, repeat="once", **kw):
    return Alarm(id=id, time=t, repeat=repeat, **kw)


def test_fires_when_window_contains_time():
    a = A(1, "07:30")
    got = due_alarms([a], datetime(2026, 10, 1, 7, 29, 59), datetime(2026, 10, 1, 7, 30, 0))
    assert [x.id for x, _ in got] == [1]


def test_does_not_fire_for_time_already_passed():
    a = A(1, "07:30")
    assert due_alarms([a], datetime(2026, 10, 1, 8, 0, 0), datetime(2026, 10, 1, 8, 0, 1)) == []


def test_two_alarms_same_minute_both_fire():
    got = due_alarms([A(1, "07:30"), A(2, "07:30")],
                     datetime(2026, 10, 1, 7, 29, 59), datetime(2026, 10, 1, 7, 30, 0))
    assert [x.id for x, _ in got] == [1, 2]


def test_last_fired_date_prevents_refire():
    a = A(1, "07:30", last_fired_date="2026-10-01")
    assert due_alarms([a], datetime(2026, 10, 1, 7, 29, 59), datetime(2026, 10, 1, 7, 30, 0)) == []


def test_midnight_rollover_window():
    a = A(1, "00:00")
    got = due_alarms([a], datetime(2026, 9, 30, 23, 59, 59), datetime(2026, 10, 1, 0, 0, 1))
    assert len(got) == 1 and got[0][1].isoformat() == "2026-10-01"


def test_late_tick_still_catches_alarm_from_previous_day_boundary():
    a = A(1, "23:59")
    got = due_alarms([a], datetime(2026, 9, 30, 23, 58, 0), datetime(2026, 10, 1, 0, 0, 30))
    assert len(got) == 1 and got[0][1].isoformat() == "2026-09-30"


def test_disabled_alarm_never_due():
    a = A(1, "07:30", enabled=False)
    assert due_alarms([a], datetime(2026, 10, 1, 7, 29), datetime(2026, 10, 1, 7, 31)) == []


def test_weekdays_skips_weekend():
    a = A(1, "07:30", "weekdays")
    sat = datetime(2026, 10, 3, 7, 29, 59)   # 2026-10-03 is a Saturday
    assert due_alarms([a], sat, sat + timedelta(seconds=1)) == []
    fri = datetime(2026, 10, 2, 7, 29, 59)
    assert len(due_alarms([a], fri, fri + timedelta(seconds=1))) == 1


def test_daily_alarm_missed_over_two_days_rings_once():
    a = A(1, "07:30", "daily")
    got = due_alarms([a], datetime(2026, 10, 1, 0, 0), datetime(2026, 10, 3, 12, 0))
    assert len(got) == 1


def test_next_fire_today_vs_tomorrow():
    a = A(1, "07:30")
    assert next_fire(a, datetime(2026, 9, 30, 6, 0)) == datetime(2026, 9, 30, 7, 30)
    assert next_fire(a, datetime(2026, 9, 30, 8, 0)) == datetime(2026, 10, 1, 7, 30)


def test_next_fire_weekdays_skips_to_monday():
    a = A(1, "07:30", "weekdays")
    assert next_fire(a, datetime(2026, 10, 2, 9, 0)) == datetime(2026, 10, 5, 7, 30)  # Fri -> Mon


def test_next_fire_none_when_disabled():
    assert next_fire(A(1, "07:30", enabled=False), datetime(2026, 9, 30, 6, 0)) is None


def test_fmt_delta():
    assert fmt_delta(timedelta(seconds=30)) == "<1m"
    assert fmt_delta(timedelta(minutes=5)) == "5m"
    assert fmt_delta(timedelta(hours=2, minutes=5, seconds=59)) == "2h 5m"
