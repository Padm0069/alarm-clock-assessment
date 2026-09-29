from datetime import datetime

import pytest

from alarm.cli import main
from alarm.ring import ring

NOW = datetime(2026, 9, 30, 10, 0, 0)


def run(tmp_path, *argv):
    return main(["--file", str(tmp_path / "a.json"), *argv], clock=lambda: NOW)


def test_add_list_remove_roundtrip(tmp_path, capsys):
    assert run(tmp_path, "add", "07:30", "--label", "Standup", "--repeat", "weekdays") == 0
    assert "Added #1" in capsys.readouterr().out

    assert run(tmp_path, "list") == 0
    out = capsys.readouterr().out
    assert "Standup" in out and "weekdays" in out and "01 Oct 07:30" in out   # already past -> tomorrow

    assert run(tmp_path, "remove", "1") == 0
    run(tmp_path, "list")
    assert "No alarms set" in capsys.readouterr().out


def test_add_relative_without_quotes(tmp_path, capsys):
    assert run(tmp_path, "add", "in", "10m") == 0
    assert "10:10" in capsys.readouterr().out


def test_add_12_hour_time(tmp_path, capsys):
    assert run(tmp_path, "add", "7:30pm") == 0
    assert "19:30" in capsys.readouterr().out


def test_invalid_time_is_friendly_error(tmp_path, capsys):
    assert run(tmp_path, "add", "25:99") == 2
    captured = capsys.readouterr()
    assert captured.err.startswith("error:") and captured.out == ""


def test_remove_unknown_id(tmp_path, capsys):
    assert run(tmp_path, "remove", "42") == 1
    assert "no alarm with id 42" in capsys.readouterr().err


def test_bad_repeat_rejected_by_argparse(tmp_path):
    with pytest.raises(SystemExit) as e:
        run(tmp_path, "add", "07:30", "--repeat", "monthly")
    assert e.value.code == 2


def test_ring_snooze_and_dismiss(capsys):
    class Al:
        time, label = "07:30", "x"
    quiet = dict(sleep=lambda s: None)
    assert ring([Al], NOW, read_line=lambda: "s", **quiet) == "snooze"
    assert ring([Al], NOW, read_line=lambda: "", **quiet) == "dismiss"
    assert ring([Al], NOW, read_line=lambda: (_ for _ in ()).throw(EOFError), **quiet) == "dismiss"
