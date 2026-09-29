# alarm-clock

A small, dependable alarm clock for the terminal.
Python 3.9+ · **standard library only** · state in one JSON file · 66 tests that run in ~0.2 s.

```text
$ alarm add 07:30 --label "Standup" --repeat weekdays
Added #1: 07:30 'Standup' [weekdays] - next: Thu 01 Oct 07:30 (in 9h 12m)

$ alarm run
Alarm clock running. Press Ctrl+C to stop.

============================================
  ALARM 07:30  Standup
============================================
  [Enter] dismiss    [s + Enter] snooze 5 min
```

---

## Contents

1. [Quick start](#quick-start)
2. [Features](#features)
3. [Usage](#usage)
4. [How it works](#how-it-works)
5. [Design principles](#design-principles)
6. [Key code, explained](#key-code-explained)
7. [Edge cases](#edge-cases)
8. [Testing](#testing)
9. [Known limitations](#known-limitations)
10. [What I would build next](#what-i-would-build-next)
11. [How this was built (AI workflow)](#how-this-was-built-ai-workflow)

---

## Quick start

You need Python 3.9 or newer. Run everything from the folder that contains `pyproject.toml`.

> **Unzipped it and can't find `pyproject.toml`?** Extracting often creates a nested folder
> (`alarm-clock\alarm-clock`). Run `dir`, and `cd alarm-clock` again if needed.

### Windows (PowerShell)

```powershell
# 1. create a virtual environment
python -m venv .venv

# 2. install the project + pytest (no activation needed)
.venv\Scripts\python -m pip install -e ".[dev]"

# 3. run the tests (expect: 66 passed)
.venv\Scripts\python -m pytest

# 4. use it
.venv\Scripts\python -m alarm add in 1m --label "demo"
.venv\Scripts\python -m alarm run
```

Optional: activate the venv so you can type `alarm ...` directly.

```powershell
.venv\Scripts\Activate.ps1
alarm list
```

If PowerShell says scripts are disabled, allow them for this terminal only, then activate again:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

> `source .venv/bin/activate` is a macOS/Linux command. It does not exist in PowerShell.

**No virtual environment at all?** The app has no dependencies, so this works too:

```powershell
pip install pytest
python -m pytest
python -m alarm add in 1m --label "demo"
python -m alarm run
```

### macOS / Linux

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
python -m pytest
alarm add in 1m --label "demo"
alarm run
```

### Where data is stored

`~/.alarm-clock/alarms.json` (Windows: `C:\Users\<you>\.alarm-clock\alarms.json`).
Override it per command with `--file PATH`, or for the session with an environment variable:

```powershell
$env:ALARM_FILE = "$env:TEMP\demo-alarms.json"     # PowerShell
```
```bash
export ALARM_FILE=/tmp/demo-alarms.json            # macOS / Linux
```

---

## Features

| Feature | Details |
|---|---|
| **Flexible time input** | `07:30`, `7:30am`, `7pm`, `12am` (midnight), `12pm` (noon), `in 10m`, `in 2h`, `in 1h30m` |
| **Labels** | `--label "Standup"` is shown when the alarm rings |
| **Repeat modes** | `once` (default), `daily`, `weekdays` (skips Saturday and Sunday) |
| **List** | Every alarm with its state and its *next* ring time plus a countdown |
| **Remove** | By id; ids are never reused |
| **Run loop** | Foreground loop that rings with the terminal bell and a visible banner |
| **Dismiss / snooze** | `Enter` dismisses, `s` + `Enter` snoozes (default 5 min, `--snooze N` to change) |
| **Live countdown** | While running: `Next: 07:30 Standup - in 2h 5m` |
| **Live updates** | Add or remove alarms from a second terminal while `run` is going; it picks them up within a second |
| **Persistence** | One JSON file, atomic writes, corrupt-file recovery |
| **Friendly errors** | Clear message and a non-zero exit code for bad input; never a stack trace |

---

## Usage

```text
alarm add <time> [--label TEXT] [--repeat once|daily|weekdays]
alarm list
alarm remove <id>
alarm run [--snooze MIN]
alarm [--file PATH] <command>
```

### Examples

```powershell
alarm add 07:30 --label "Standup" --repeat weekdays
alarm add 7:30pm --label "Dinner"
alarm add in 25m --label "Tea"
alarm list
alarm remove 2
alarm run --snooze 10
```

Sample `list` output:

```text
ID  TIME   REPEAT    STATE  NEXT                                LABEL
1   07:30  weekdays  on     Thu 01 Oct 07:30 (in 9h 12m)        Standup
2   19:30  once      on     Wed 30 Sep 19:30 (in 1h 40m)        Dinner
3   14:05  once      done   -                                   Tea
```

Input that is rejected on purpose (message + exit code 2, nothing saved):

```text
alarm add 25:99       # hour out of range
alarm add 7           # ambiguous: am or pm?
alarm add 7:30xyz     # trailing junk is not silently ignored
alarm add in 0m       # zero duration
alarm add in 25h      # a stored HH:MM can't represent "a day or more"
```

---

## How it works

```text
                     ┌──────────────┐
   argv ───────────► │   cli.py     │  argparse, output formatting, exit codes
                     └──────┬───────┘
          ┌─────────────────┼───────────────────────┐
          ▼                 ▼                       ▼
   ┌────────────┐    ┌────────────┐          ┌─────────────┐
   │ parser.py  │    │  store.py  │          │  runner.py  │  1-second loop
   │ text→time  │    │ JSON, atomic│         └──────┬──────┘
   └────────────┘    └─────┬──────┘                 │
                           ▲             ┌──────────┴───────────┐
                           │             ▼                      ▼
                           │      ┌────────────┐          ┌───────────┐
                           └──────│ models.py  │          │  ring.py  │
                        mark_fired│ pure logic │          │ bell + I/O│
                                  └────────────┘          └───────────┘
```

| Module | Responsibility | Does I/O? |
|---|---|---|
| `parser.py` | Turns `"in 10m"` / `"7:30pm"` into a `time` | No (`now` is passed in) |
| `models.py` | `Alarm` dataclass, `due_alarms`, `next_fire`, `fmt_delta` | No |
| `store.py` | Load / add / remove / mark-fired, atomic save, corrupt-file handling | File only |
| `runner.py` | The polling loop | Only through injected functions |
| `ring.py` | Banner, terminal bell, reads Enter / `s` | Terminal |
| `cli.py` | Wires it all together | Terminal |

**What happens on `alarm run`, tick by tick:**

1. Read the current time from the (injectable) clock.
2. Re-load the alarm file, so changes from other terminals are seen.
3. Ask `due_alarms` which alarms fell inside the window `(previous tick, now]`.
4. Save "fired" for each one **before** ringing.
5. Add any snoozed alarms whose wake-up time has arrived.
6. Move the window forward, then ring (blocks until you answer), or update the countdown line.
7. Sleep one second and repeat.

---

## Design principles

1. **Pure logic, thin I/O.** Everything that decides *when* to ring (`parser.py`, `models.py`) does no I/O and never calls `datetime.now()`. Time, sleep, ringing and input are passed in. The riskiest logic is therefore testable in milliseconds with a fake clock, and no test ever sleeps.
2. **An alarm is a time of day, not a datetime.** "The time already passed today, so schedule it for tomorrow" needs no special case: the alarm simply hasn't matched yet. `in 10m` is converted to `HH:MM` when it is added.
3. **Fire on a window, not on equality.** `now == alarm_time` loses alarms if the loop is busy for a second. A window `(last_tick, now]` cannot lose them, and because it starts when `run` starts, alarms whose time already passed never fire late.
4. **Persist before you ring.** "Fired" is written to disk first, so a crash or restart inside the same minute cannot ring twice.
5. **Never destroy user data.** Writes go to a temp file and are renamed into place (atomic). A corrupt file is moved aside, not deleted.
6. **Read-modify-write on every change.** A long-running `run` never overwrites an alarm you added elsewhere with a stale in-memory copy.
7. **Fail loudly and politely.** A dedicated `ParseError` becomes a one-line message with exit code 2; real bugs are not swallowed.
8. **Reject ambiguity instead of guessing.** A bare `7` is not silently treated as am or pm.
9. **Zero dependencies.** Nothing to install for the app itself; `pytest` is only for the tests.
10. **Small on purpose.** Scope was cut early (no daemon, no timezones, no audio files) and the limits are documented below rather than hidden.

---

## Key code, explained

### 1. Parsing that can't be fooled (`parser.py`)

```python
_CLOCK = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.ASCII)

if meridiem:
    if not 1 <= hour <= 12:
        raise ParseError("12-hour times need an hour from 1 to 12")
    hour = hour % 12 + (12 if meridiem == "pm" else 0)   # 12am->0, 12pm->12
```

- `fullmatch` means the *whole* string must match, so `7:30xyz` is an error rather than 7:30.
- `hour % 12` maps 12 to 0, then pm adds 12. Midnight (`12am` = 0) and noon (`12pm` = 12) fall out of the arithmetic with no special cases.

### 2. Deciding what is due (`models.py`)

```python
def due_alarms(alarms, after, upto):
    """Alarms whose ring time falls in the window (after, upto]."""
    found = {}
    day = after.date()
    while day <= upto.date():                      # handles midnight rollover
        for a in alarms:
            if not a.enabled or not a.runs_on(day):   # runs_on: weekdays rule
                continue
            fire_at = datetime.combine(day, a.time_of_day())
            if after < fire_at <= upto and a.last_fired_date != day.isoformat():
                found[a.id] = (fire_at, a, day)       # one entry per alarm
        day += timedelta(days=1)
    ...
```

- The window is what makes it robust: a blocked loop, a brief sleep, or a tick that crosses midnight can't skip an alarm.
- `last_fired_date` prevents a second ring for the same day.
- Keyed by alarm id, so a daily alarm missed for several days rings **once**, not once per missed day.

### 3. Crash-safe saving (`store.py`)

```python
fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".alarms-", suffix=".tmp")
with os.fdopen(fd, "w", encoding="utf-8") as f:
    json.dump(payload, f, indent=2)
    f.flush()
    os.fsync(f.fileno())
os.replace(tmp, self.path)      # atomic: readers see the old file or the new one
```

- The temp file is in the **same directory**, which is what makes the rename atomic.
- If anything fails, the temp file is deleted and the original file is untouched. There is a test that forces `os.replace` to fail.

### 4. The run loop with injected dependencies (`runner.py`)

```python
def run_loop(store, clock, sleep, ring, snooze_minutes=5, status=None, max_ticks=None):
    last_check = clock()
    while max_ticks is None or ticks < max_ticks:
        now = clock()
        for alarm, day in due_alarms(store.load(), last_check, now):
            store.mark_fired(alarm.id, day)       # persist BEFORE ringing
            ringing.append(alarm)
        last_check = now                          # advance BEFORE the blocking ring
        if ringing and ring(ringing, now) == "snooze":
            ...
        sleep(1)
```

- Advancing `last_check` **before** the blocking `ring()` call is deliberate: an alarm that comes due while you're answering another one is caught by the next tick.
- `clock`, `sleep` and `ring` are parameters. Production passes `datetime.now`, `time.sleep` and the real ringer; tests pass fakes.

### 5. Ringing without blocking the bell (`ring.py`)

```python
threading.Thread(target=_reader, daemon=True).start()   # waits for Enter / "s"
while not answer:
    out.write("\a"); out.flush()                        # bell once a second
    sleep(1)
```

- Reading input on a background thread lets the main thread keep sounding the bell. It is pure standard library and works on every OS.
- A closed stdin (`EOFError`) counts as "dismiss", so it can't ring forever.

### 6. A test that needs no waiting

```python
def test_alarm_that_comes_due_while_ringing_is_not_lost(tmp_path):
    store, t = make(tmp_path, datetime(2026, 10, 1, 7, 29, 59))
    store.add("07:30", "A")
    store.add("07:31", "B")

    def slow_ring(alarms, now):              # the user takes 2 minutes to react
        rings.append([a.label for a in alarms])
        t.now += timedelta(minutes=2)
        return "dismiss"

    run_loop(store, t.clock, t.sleep, slow_ring, max_ticks=5)
    assert rings == [["A"], ["B"]]
```

A two-minute scenario runs in a few milliseconds because time is a fake.

---

## Edge cases

**Handled and covered by tests**

| Case | Behaviour |
|---|---|
| `25:99`, `abc`, `7`, `7:30xyz`, `in 0m`, `in 25h` | Clear error, exit code 2, nothing saved |
| `12:00am` / `12:00pm` | Stored as `00:00` / `12:00` |
| `in 10m` at 23:55 | Crosses midnight correctly |
| Time already passed today | Next ring shown as tomorrow; does not fire late |
| Two alarms in the same minute | Both ring, together, once |
| Loop running for the whole minute | Rings once, not 60 times (`last_fired_date`) |
| An alarm comes due while another is ringing | Not lost; rings on the next tick |
| Daily alarm missed for several days | Rings once |
| `weekdays` on a Friday | Next ring is Monday |
| Missing JSON file | Treated as empty |
| Corrupt or invalid JSON | Warning, file moved to `*.corrupt`, starts empty |
| Save fails halfway | Original file intact, no temp files left |
| Remove an unknown id | Friendly message, exit code 1 |
| stdin closed while ringing | Treated as dismiss |
| Ctrl+C during `run` | Clean exit |

---

## Testing

```powershell
python -m pytest -q                       # everything: 66 tests
python -m pytest tests/test_runner.py -v  # the time-travel scenarios
```

| File | Covers |
|---|---|
| `test_parser.py` | Every accepted and rejected time format |
| `test_models.py` | Window firing, midnight, weekdays, `next_fire` |
| `test_store.py` | Persistence, id reuse, corruption, atomic writes |
| `test_runner.py` | Fake-clock scenarios: snooze, double-fire, live add |
| `test_cli.py` | End-to-end commands, exit codes, ring answers |

---

## Known limitations

These are deliberate scope cuts, not oversights.

- **DST and timezones.** Alarms use local wall-clock time. A spring-forward can skip a `02:30` alarm.
- **Snooze lives in memory.** Restarting `run` forgets a pending snooze.
- **Alarms missed while `run` isn't running** are skipped silently.
- **Two processes writing in the same instant** can lose an update (no file locking).
- **Relative times round down to the minute.** At 10:00:45, `in 10m` rings at 10:10:00.
- **Audio is the terminal bell only.** Some terminals, including some VS Code and PowerShell setups, mute it; the banner is the reliable alert.
- **Not a service.** `run` must stay open in a terminal.

---

## What I would build next

**Reliability**
1. "You missed..." summary when `run` starts.
2. Persist snooze to disk.
3. File locking so concurrent writers are safe.
4. `zoneinfo` timezone support and explicit DST rules.

**Features**
5. `edit`, `enable` and `disable` commands.
6. Custom repeat days: `--repeat mon,wed,fri`.
7. Increasing snooze, or a maximum snooze count.
8. Natural-language times: `tomorrow 9am`, `next monday 7:00`.

**Experience**
9. OS notifications and a real sound (optional dependency).
10. Run as a background service (Windows Task Scheduler / systemd), with `run` becoming a client.
11. Colour output and a `--json` flag for scripting.
12. A pseudo-terminal test for the threaded ring prompt.
13. CI (GitHub Actions) running the tests on Windows, macOS and Linux.

---

## How this was built (AI workflow)

Requirements, design and edge cases were worked out *before* any code was written, then cut down deliberately: no daemon, no timezones, no audio dependency. The plan is in [`docs/PLAN.md`](docs/PLAN.md).

The build then went one step at a time (parser, store, CLI, run loop, repeats, edge-case tests), running the tests after each. One design changed along the way: firing moved from an exact time match to a time window once it was clear an alarm could be lost while another one was ringing. That decision is covered by a test.

## Project layout

```text
alarm-clock/
├── README.md
├── pyproject.toml
├── docs/PLAN.md
├── alarm/
│   ├── __init__.py
│   ├── __main__.py      # python -m alarm
│   ├── cli.py
│   ├── models.py
│   ├── parser.py
│   ├── ring.py
│   ├── runner.py
│   └── store.py
└── tests/
    ├── test_cli.py
    ├── test_models.py
    ├── test_parser.py
    ├── test_runner.py
    └── test_store.py
```
