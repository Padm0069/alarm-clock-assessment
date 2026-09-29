"""Alarm data model and the pure scheduling logic (no I/O, no clock)."""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import Optional

REPEATS = ("once", "daily", "weekdays")


@dataclass
class Alarm:
    id: int
    time: str                                  # "HH:MM", 24h
    label: str = ""
    repeat: str = "once"                       # once | daily | weekdays
    enabled: bool = True
    last_fired_date: Optional[str] = None      # ISO date; guards double-firing

    def validate(self) -> None:
        if self.repeat not in REPEATS:
            raise ValueError(f"bad repeat {self.repeat!r}")
        dt.time.fromisoformat(self.time)       # raises ValueError if bad
        if not isinstance(self.id, int) or isinstance(self.id, bool):
            raise ValueError("id must be an int")

    def time_of_day(self) -> dt.time:
        return dt.time.fromisoformat(self.time)

    def runs_on(self, day: dt.date) -> bool:
        return self.repeat != "weekdays" or day.weekday() < 5


def due_alarms(alarms, after: dt.datetime, upto: dt.datetime):
    """Alarms whose ring time falls in the window (after, upto].

    Using a *window* instead of "does HH:MM equal now?" means an alarm is not
    missed if the loop was blocked (e.g. another alarm was ringing) or the
    laptop slept for a few seconds. And because the window starts when `run`
    started, an alarm for a time that already passed today does not fire.

    Returns [(alarm, day_it_was_due)], at most one entry per alarm.
    """
    found = {}
    day = after.date()
    while day <= upto.date():
        for a in alarms:
            if not a.enabled or not a.runs_on(day):
                continue
            fire_at = dt.datetime.combine(day, a.time_of_day())
            if after < fire_at <= upto and a.last_fired_date != day.isoformat():
                found[a.id] = (fire_at, a, day)
        day += dt.timedelta(days=1)
    return [(a, d) for _, a, d in sorted(found.values(), key=lambda t: (t[0], t[1].id))]


def next_fire(alarm: Alarm, now: dt.datetime) -> Optional[dt.datetime]:
    """Next datetime this alarm will ring, or None if it never will."""
    if not alarm.enabled:
        return None
    for offset in range(8):                    # a week always contains a match
        day = now.date() + dt.timedelta(days=offset)
        if not alarm.runs_on(day) or alarm.last_fired_date == day.isoformat():
            continue
        candidate = dt.datetime.combine(day, alarm.time_of_day())
        if candidate > now:
            return candidate
    return None


def fmt_delta(delta: dt.timedelta) -> str:
    minutes = int(delta.total_seconds() // 60)
    if minutes < 1:
        return "<1m"
    h, m = divmod(minutes, 60)
    return f"{h}h {m}m" if h else f"{m}m"
