"""JSON-file persistence: atomic writes, tolerant reads."""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
import tempfile
from dataclasses import asdict
from pathlib import Path
from typing import Callable, List, Tuple

from .models import Alarm


def _stderr_warn(msg: str) -> None:
    print(f"warning: {msg}", file=sys.stderr)


class Store:
    """All alarm state lives in one small JSON file.

    Every mutating method is load -> change -> atomic save, so a long-running
    `run` never overwrites an alarm added from another terminal with a stale
    in-memory copy. (Two writers in the *same instant* is still a race; see README.)
    """

    def __init__(self, path, warn: Callable[[str], None] = _stderr_warn):
        self.path = Path(path)
        self.warn = warn

    # ---- reading ----
    def load(self) -> List[Alarm]:
        return self._read()[0]

    def _read(self) -> Tuple[List[Alarm], int]:
        try:
            raw = self.path.read_text(encoding="utf-8")
        except FileNotFoundError:
            return [], 1
        try:
            data = json.loads(raw)
            alarms = [Alarm(**a) for a in data["alarms"]]
            for a in alarms:
                a.validate()
            if len({a.id for a in alarms}) != len(alarms):
                raise ValueError("duplicate ids")
            next_id = max([int(data["next_id"])] + [a.id + 1 for a in alarms])
            return alarms, next_id
        except (ValueError, KeyError, TypeError) as exc:
            backup = self._quarantine()
            self.warn(f"{self.path} is unreadable ({exc}); moved to {backup}, starting empty")
            return [], 1

    def _quarantine(self) -> Path:
        """Keep the bad file (never destroy user data) and free the path."""
        backup = Path(str(self.path) + ".corrupt")
        os.replace(self.path, backup)
        return backup

    # ---- writing ----
    def _write(self, alarms: List[Alarm], next_id: int) -> None:
        payload = {"next_id": next_id, "alarms": [asdict(a) for a in alarms]}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Temp file in the SAME directory so os.replace is an atomic rename.
        fd, tmp = tempfile.mkstemp(dir=self.path.parent, prefix=".alarms-", suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, self.path)
        except BaseException:
            try:
                os.unlink(tmp)
            except FileNotFoundError:
                pass
            raise

    def add(self, time_str: str, label: str = "", repeat: str = "once") -> Alarm:
        alarms, next_id = self._read()
        alarm = Alarm(id=next_id, time=time_str, label=label, repeat=repeat)
        alarm.validate()
        alarms.append(alarm)
        self._write(alarms, next_id + 1)          # ids are never reused
        return alarm

    def remove(self, alarm_id: int) -> bool:
        alarms, next_id = self._read()
        kept = [a for a in alarms if a.id != alarm_id]
        if len(kept) == len(alarms):
            return False
        self._write(kept, next_id)
        return True

    def mark_fired(self, alarm_id: int, day: dt.date) -> None:
        alarms, next_id = self._read()
        for a in alarms:
            if a.id == alarm_id:
                a.last_fired_date = day.isoformat()
                if a.repeat == "once":
                    a.enabled = False
                self._write(alarms, next_id)
                return
