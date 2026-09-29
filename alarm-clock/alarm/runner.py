"""The foreground loop behind `alarm run`. Clock, sleep and ring are injected."""
from __future__ import annotations

import datetime as dt

from .models import due_alarms


def run_loop(store, clock, sleep, ring, snooze_minutes=5, status=None, max_ticks=None):
    """Poll once a second; ring whatever came due since the previous tick.

    ring(alarms, now) -> "dismiss" | "snooze"
    status(now, alarms) is called every tick (used for the live countdown).
    max_ticks exists only so tests can stop the loop.
    """
    last_check = clock()          # alarms before this moment are not "due"
    snoozed = []                  # [(wake_at, alarm)] - in memory only
    ticks = 0

    while max_ticks is None or ticks < max_ticks:
        now = clock()
        alarms = store.load()     # re-read: picks up add/remove from other terminals

        ringing = []
        for alarm, day in due_alarms(alarms, last_check, now):
            store.mark_fired(alarm.id, day)   # persist BEFORE ringing (crash-safe)
            ringing.append(alarm)

        still_asleep = []
        for wake_at, alarm in snoozed:
            if wake_at <= now:
                if all(alarm.id != r.id for r in ringing):
                    ringing.append(alarm)
            else:
                still_asleep.append((wake_at, alarm))
        snoozed = still_asleep

        # Advance the window BEFORE ringing. Ringing blocks; anything that comes
        # due while the user is answering is caught by the next tick's window.
        last_check = now

        if ringing:
            if ring(ringing, now) == "snooze":
                wake = now + dt.timedelta(minutes=snooze_minutes)
                snoozed.extend((wake, a) for a in ringing)
        elif status:
            status(now, alarms)

        ticks += 1
        sleep(1)
