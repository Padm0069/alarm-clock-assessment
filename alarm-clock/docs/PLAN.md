# Plan (written before coding)

Constraint: 30 minutes, no spec, CLI only, no web UI / React / database.
Judged on process and AI usage more than feature count.

## Requirements

**Must:** add (`07:30`, `7:30am`, `in 10m`, label) / list / remove / run (ring in foreground) / dismiss or snooze / JSON persistence.
**Should:** repeat modes (once, daily, weekdays), live countdown.
**Out of scope (on purpose):** daemon, OS notifications, sound files, timezones, GUI.

## Design

- Modules: parser, models (pure logic), store, runner, ring, cli.
- Alarm = time of day + label + repeat + enabled + last_fired_date.
- Injected clock for tests. Poll every 1s. Stdlib only.

## Edge cases

Build: invalid input, past time -> tomorrow, midnight and 12am/12pm, same-minute alarms, no double-firing, corrupt/missing JSON, atomic save, Ctrl+C, unknown id.
Document only: DST/timezones, missed alarms while not running, concurrent writers, cross-platform audio.

## Build order (each step runnable)

1. Parser + tests
2. Store (atomic save, corrupt handling)
3. CLI add/list/remove
4. Run loop + ring + snooze
5. Repeat modes + countdown
6. Edge-case tests, README

## Decisions made while building

- Firing uses a `(last_tick, now]` window rather than `HH:MM == now`, so alarms aren't lost while another one is ringing.
- `in 24h`+ rejected: HH:MM storage can't represent it.
- Snooze kept in memory (persisted snooze deferred).
