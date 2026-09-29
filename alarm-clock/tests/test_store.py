import json
from datetime import date

import pytest

from alarm.store import Store


@pytest.fixture
def warnings():
    return []


@pytest.fixture
def store(tmp_path, warnings):
    return Store(tmp_path / "sub" / "alarms.json", warn=warnings.append)


def test_missing_file_is_empty(store):
    assert store.load() == []


def test_add_persists_and_creates_parent_dir(store):
    a = store.add("07:30", "Standup", "daily")
    assert a.id == 1
    again = Store(store.path).load()
    assert [(x.time, x.label, x.repeat) for x in again] == [("07:30", "Standup", "daily")]


def test_ids_never_reused(store):
    store.add("07:30")
    store.add("08:00")
    store.remove(2)
    assert store.add("09:00").id == 3


def test_remove_missing_returns_false(store):
    assert store.remove(99) is False


def test_corrupt_file_is_quarantined_not_destroyed(store, warnings):
    store.path.parent.mkdir(parents=True)
    store.path.write_text("{not json")
    assert store.load() == []
    assert warnings and "unreadable" in warnings[0]
    assert (store.path.parent / "alarms.json.corrupt").read_text() == "{not json"
    store.add("07:30")                      # store is usable again
    assert len(store.load()) == 1


def test_invalid_alarm_content_counts_as_corrupt(store, warnings):
    store.path.parent.mkdir(parents=True)
    store.path.write_text(json.dumps({"next_id": 2, "alarms": [{"id": 1, "time": "99:99"}]}))
    assert store.load() == []
    assert warnings


def test_mark_fired_disables_once_but_not_daily(store):
    once = store.add("07:30", repeat="once")
    daily = store.add("07:30", repeat="daily")
    store.mark_fired(once.id, date(2026, 10, 1))
    store.mark_fired(daily.id, date(2026, 10, 1))
    by_id = {a.id: a for a in store.load()}
    assert by_id[once.id].enabled is False
    assert by_id[daily.id].enabled is True
    assert by_id[daily.id].last_fired_date == "2026-10-01"


def test_no_temp_files_left_behind(store):
    store.add("07:30")
    assert [p.name for p in store.path.parent.iterdir()] == ["alarms.json"]


def test_failed_write_leaves_original_intact(store, monkeypatch):
    store.add("07:30")
    before = store.path.read_text()

    def boom(*a, **k):
        raise OSError("disk full")
    monkeypatch.setattr("alarm.store.os.replace", boom)
    with pytest.raises(OSError):
        store.add("08:00")
    monkeypatch.undo()
    assert store.path.read_text() == before
    assert [p.name for p in store.path.parent.iterdir()] == ["alarms.json"]
