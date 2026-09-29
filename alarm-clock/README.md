# alarm-clock

A small terminal alarm clock. Python 3.9+, **standard library only**, state in one JSON file.

```
$ alarm add 07:30 --label "Standup" --repeat weekdays
Added #1: 07:30 'Standup' [weekdays] - next: Thu 01 Oct 07:30 (in 9h 12m)
$ alarm run
```

## Run it

```bash
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"        # installs the `alarm` command + pytest
python -m pytest               # 66 tests, ~0.2s
```

No install needed either: `python -m alarm <command>` works from the repo root.

## Usage

| Command | What it does |
|---|---|
| `alarm add 07:30` | 24h time |
| `alarm add 7:30am` / `7pm` | 12h time (a bare `7` is rejected as ambiguous) |
| `alarm add in 10m` / `in 1h30m` | relative; quotes optional |
| `alarm add ... --label "Standup"` | text shown when ringing |
| `alarm add ... --repeat once\|daily\|weekdays` | default `once` |
| `alarm list` | all alarms + next ring time |
| `alarm remove <id>` | delete |
| `alarm run [--snooze 5]` | stay in the foreground and ring |

While ringing: **Enter** dismisses, **`s` + Enter** snoozes (default 5 min). `Ctrl+C` stops `run` cleanly.

State file: `~/.alarm-clock/alarms.json` (override with `--file` or `$ALARM_FILE`).
`alarm add` and `alarm remove` can be used from a second terminal while `run` is going; the loop re-reads the file every tick.

## How it works

```
argv -> cli.py --parse--> parser.py  ("in 10m" -> time(10,10))
           |
           +--> store.py  (JSON: load -> change -> atomic save)
           |
           `--> runner.py (1s loop) --uses--> models.due_alarms(store, window)
                              `--on due--> ring.py (bell + Enter/s)
```

| Module | Responsibility | Touches I/O? |
|---|---|---|
| `parser.py` | text -> `time` | no (`now` injected) |
| `models.py` | `Alarm`, `due_alarms`, `next_fire` (all scheduling logic) | no |
| `store.py` | JSON persistence | file only |
| `runner.py` | the polling loop | via injected `clock`/`sleep`/`ring` |
| `ring.py` | bell + banner + read answer | terminal |
| `cli.py` | argparse, output formatting | terminal |

## Design decisions

1. **An alarm is a time of day, not a datetime.** "Already passed today -> tomorrow" needs no special case; it simply hasn't matched yet. `in 10m` is converted to `HH:MM` at add time.
2. **Window-based firing, not `now == alarm_time`.** An alarm is due if its time is in `(last_tick, now]`. This survives a blocked loop (another alarm ringing), a laptop sleeping a few seconds, and midnight rollover, and it never fires alarms whose time passed before `run` started.
3. **Injected clock / sleep / ring / input.** The riskiest logic (time) is tested with a fake clock in milliseconds. No test sleeps.
4. **Poll every 1s** instead of sleeping until the next alarm: simpler, and robust to clock changes and suspend.
5. **Persist "fired" before ringing** (`last_fired_date`, and `once` alarms become `done`), so a crash or restart in the same minute can't double-ring.
6. **Atomic save:** write a temp file in the same directory, `fsync`, then `os.replace`. Ctrl+C mid-save can't corrupt the store.
7. **Corrupt file is quarantined, not deleted:** moved to `alarms.json.corrupt`, a warning is printed, and the app starts empty.
8. **Read-modify-write on every change** so `run` doesn't clobber alarms added from another terminal with a stale copy.
9. **Threaded input while ringing:** one thread waits for Enter, the main thread rings the bell each second. Pure stdlib, cross-platform.
10. **Ids are never reused** (`next_id` counter), so `remove 3` can't hit a different alarm than `list` showed.
11. **Rejected on purpose:** bare `7` (am/pm?), `in 24h`+ (HH:MM can't represent it), `25:99`, trailing junk like `7:30xyz`.

## Edge cases

Handled and tested: invalid times, past time -> tomorrow, midnight/noon (`12am`/`12pm`), `in` crossing midnight, two alarms in the same minute, once-per-minute firing, alarm due while another is ringing, daily alarm missed over several days rings once, weekday skipping, corrupt/missing/invalid JSON, failed write leaves the original file intact, unknown id, closed stdin, Ctrl+C.

Known limits (deliberately not built):
- **DST / timezones:** alarms use local wall-clock time. Spring-forward can skip a `02:30` alarm.
- **Snooze is in memory.** Restarting `run` forgets a pending snooze.
- **Missed alarms while `run` wasn't running** are silently skipped (no "you missed..." summary).
- **Two processes writing in the same instant** can lose an update (needs file locking).
- **Relative times round down to the minute:** at 10:00:45, `in 10m` rings at 10:10:00.
- **Audio** is the terminal bell only (some terminals mute it).
- Not a daemon: `run` must stay open.

## With more time

Missed-alarm summary on start, persisted snooze, file locking, `enable/disable/edit`, weekday-set repeats (`--repeat mon,wed`), OS notifications, `zoneinfo` timezones.

## AI workflow

See [`docs/PLAN.md`](docs/PLAN.md) for the requirements, edge-case ranking and build plan produced (and cut down) before writing code.
