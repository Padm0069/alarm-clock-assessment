"""Parse user-supplied time strings into a time-of-day."""
import re
from datetime import datetime, time, timedelta


class ParseError(ValueError):
    """Raised when a time string can't be understood."""


# "7", "7:30", "07:30" + optional am/pm. Whole string must match.
_CLOCK = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.ASCII)
# "10m", "2h", "1h30m" (spaces already stripped before matching)
_REL = re.compile(r"(?:(\d+)h)?(?:(\d+)m)?", re.ASCII)


def parse_time(text: str, now: datetime) -> time:
    """Return the time of day for `text`. `now` is injected for testability."""
    s = text.strip().lower()
    if s == "in" or s.startswith("in "):
        return _parse_relative(s[2:].replace(" ", ""), now)
    return _parse_clock(s)


def _parse_relative(rest: str, now: datetime) -> time:
    m = _REL.fullmatch(rest)
    if not rest or not m:
        raise ParseError("use e.g. 'in 10m', 'in 2h' or 'in 1h30m'")
    total = int(m.group(1) or 0) * 60 + int(m.group(2) or 0)
    if total <= 0:
        raise ParseError("duration must be greater than zero")
    if total >= 24 * 60:
        # An alarm stores only HH:MM, so 25h would silently mean "in 1h".
        raise ParseError("durations must be under 24 hours")
    return (now + timedelta(minutes=total)).time().replace(second=0, microsecond=0)


def _parse_clock(s: str) -> time:
    m = _CLOCK.fullmatch(s)
    if not m:
        raise ParseError(f"can't parse {s!r}; try 07:30, 7:30am or 'in 10m'")
    hour, minute, meridiem = int(m.group(1)), int(m.group(2) or 0), m.group(3)

    # A bare "7" is ambiguous (am or pm?), so require a colon or am/pm.
    if m.group(2) is None and meridiem is None:
        raise ParseError(f"{s!r} is ambiguous; add am/pm or use HH:MM")

    if meridiem:
        if not 1 <= hour <= 12:
            raise ParseError("12-hour times need an hour from 1 to 12")
        hour = hour % 12 + (12 if meridiem == "pm" else 0)  # 12am->0, 12pm->12
    elif hour > 23:
        raise ParseError("hour must be 0-23")

    if minute > 59:
        raise ParseError("minute must be 0-59")
    return time(hour, minute)
