from datetime import datetime, time

import pytest

from alarm.parser import ParseError, parse_time

# Late-night "now" so relative times cross midnight.
NOW = datetime(2026, 9, 30, 23, 55)


@pytest.mark.parametrize("text, expected", [
    ("07:30", time(7, 30)),
    ("7:30", time(7, 30)),
    ("23:59", time(23, 59)),
    ("7:30am", time(7, 30)),
    ("7:30 PM", time(19, 30)),
    ("7am", time(7, 0)),
    ("12:00am", time(0, 0)),    # midnight
    ("12:00pm", time(12, 0)),   # noon
    ("12am", time(0, 0)),
    ("in 10m", time(0, 5)),     # crosses midnight
    ("in 2h", time(1, 55)),
    ("in 1h30m", time(1, 25)),
    ("  In 5 m ", time(0, 0)),  # messy input
    ("in 23h59m", time(23, 54)),
])
def test_valid(text, expected):
    assert parse_time(text, NOW) == expected


@pytest.mark.parametrize("text", [
    "", "abc", "25:99", "24:00", "7:60",
    "13:00pm", "0:30am",   # invalid 12-hour values
    "7",                   # ambiguous: 7am or 7pm?
    "7:30xyz",             # trailing junk must not be ignored
    "in", "in 0m", "in xm",
    "in 24h", "in 25h",    # HH:MM storage can't represent >= 1 day
    "in 99999999999h",
])
def test_invalid(text):
    with pytest.raises(ParseError):
        parse_time(text, NOW)


def test_relative_rounds_down_to_the_minute():
    assert parse_time("in 10m", datetime(2026, 9, 30, 10, 0, 45)) == time(10, 10)
