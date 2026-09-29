"""What happens when an alarm goes off: bell + banner until the user answers."""
from __future__ import annotations

import sys
import threading
import time as _time


def ring(alarms, now, snooze_minutes: int = 5, *, read_line=input,
         sleep=_time.sleep, out=None) -> str:
    """Ring until the user answers. Returns "dismiss" or "snooze".

    Input is read on a background thread so the main thread can keep sounding
    the terminal bell once a second. Stdlib-only and works on any OS.
    """
    out = out or sys.stdout
    out.write("\n" + "=" * 44 + "\n")
    for a in alarms:
        out.write(f"  ALARM {a.time}  {a.label or '(no label)'}\n")
    out.write("=" * 44 + "\n")
    out.write(f"  [Enter] dismiss    [s + Enter] snooze {snooze_minutes} min\n")
    out.flush()

    answer = []

    def _reader():
        try:
            answer.append(read_line())
        except EOFError:                      # stdin closed: don't ring forever
            answer.append("")

    threading.Thread(target=_reader, daemon=True).start()
    while not answer:
        out.write("\a")
        out.flush()
        sleep(1)
    return "snooze" if answer[0].strip().lower() in ("s", "snooze") else "dismiss"
