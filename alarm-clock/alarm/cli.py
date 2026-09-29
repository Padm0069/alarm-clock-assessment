"""Command-line interface: argparse wiring + output formatting."""
from __future__ import annotations

import argparse
import os
import sys
import time as _time
from datetime import datetime
from pathlib import Path

from .models import REPEATS, fmt_delta, next_fire
from .parser import ParseError, parse_time
from .ring import ring
from .runner import run_loop
from .store import Store


def default_path() -> Path:
    return Path(os.environ.get("ALARM_FILE") or Path.home() / ".alarm-clock" / "alarms.json")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="alarm", description="A tiny terminal alarm clock.")
    p.add_argument("--file", type=Path, help="alarm file (default: ~/.alarm-clock/alarms.json, or $ALARM_FILE)")
    sub = p.add_subparsers(dest="command", required=True)

    add = sub.add_parser("add", help="add an alarm, e.g.  add 07:30  |  add 7:30am  |  add in 10m")
    add.add_argument("time", nargs="+", help="07:30, 7:30am, or 'in 10m' / 'in 1h30m'")
    add.add_argument("--label", "-l", default="", help="text shown when the alarm rings")
    add.add_argument("--repeat", "-r", choices=REPEATS, default="once")

    sub.add_parser("list", help="show all alarms")

    rm = sub.add_parser("remove", help="delete an alarm by id")
    rm.add_argument("id", type=int)

    run = sub.add_parser("run", help="stay in the foreground and ring alarms")
    run.add_argument("--snooze", type=int, default=5, metavar="MIN", help="snooze length (default 5)")
    return p


def _when(alarm, now) -> str:
    nxt = next_fire(alarm, now)
    if nxt is None:
        return "-"
    return f"{nxt.strftime('%a %d %b %H:%M')} (in {fmt_delta(nxt - now)})"


def cmd_add(args, store, now) -> int:
    at = parse_time(" ".join(args.time), now)
    alarm = store.add(at.strftime("%H:%M"), args.label, args.repeat)
    label = f" '{alarm.label}'" if alarm.label else ""
    print(f"Added #{alarm.id}: {alarm.time}{label} [{alarm.repeat}] - next: {_when(alarm, now)}")
    return 0


def cmd_list(args, store, now) -> int:
    alarms = store.load()
    if not alarms:
        print("No alarms set. Try: alarm add 07:30 --label 'Standup'")
        return 0
    print(f"{'ID':<4}{'TIME':<7}{'REPEAT':<10}{'STATE':<7}{'NEXT':<36}LABEL")
    for a in sorted(alarms, key=lambda a: a.time):
        state = "on" if a.enabled else "done"
        print(f"{a.id:<4}{a.time:<7}{a.repeat:<10}{state:<7}{_when(a, now):<36}{a.label}")
    return 0


def cmd_remove(args, store, now) -> int:
    if store.remove(args.id):
        print(f"Removed #{args.id}")
        return 0
    print(f"error: no alarm with id {args.id} (see 'alarm list')", file=sys.stderr)
    return 1


def cmd_run(args, store, clock) -> int:
    live = sys.stdout.isatty()

    def status(now, alarms):
        if not live:
            return
        upcoming = [(next_fire(a, now), a) for a in alarms]
        upcoming = sorted((n, a.id, a) for n, a in upcoming if n)
        if upcoming:
            n, _, a = upcoming[0]
            text = f"Next: {n.strftime('%H:%M')} {a.label} - in {fmt_delta(n - now)}"
        else:
            text = "No upcoming alarms"
        sys.stdout.write(f"\r{text}\033[K")
        sys.stdout.flush()

    print("Alarm clock running. Press Ctrl+C to stop.")
    try:
        run_loop(store, clock, _time.sleep,
                 lambda alarms, now: ring(alarms, now, snooze_minutes=args.snooze),
                 snooze_minutes=args.snooze, status=status)
    except KeyboardInterrupt:
        print("\nStopped.")
    return 0


def main(argv=None, clock=datetime.now) -> int:
    args = build_parser().parse_args(argv)
    store = Store(args.file or default_path())
    try:
        if args.command == "run":
            return cmd_run(args, store, clock)
        handler = {"add": cmd_add, "list": cmd_list, "remove": cmd_remove}[args.command]
        return handler(args, store, clock())
    except ParseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except OSError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
