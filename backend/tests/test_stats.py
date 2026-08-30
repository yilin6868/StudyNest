from datetime import datetime, timedelta

from app.services.stats import StatsService
from app.services.store import JsonStore


def test_initial_stats(tmp_path):
    svc = StatsService(JsonStore(tmp_path))
    s = svc.get()
    assert s["tomato"] == 0
    assert s["streak"] == 0
    assert s["weekDays"] == []


def test_complete_increments(tmp_path):
    svc = StatsService(JsonStore(tmp_path))
    s = svc.complete(25)
    assert s["tomato"] == 1
    assert s["minutes"] == 25
    assert s["streak"] == 1
    assert datetime.now().strftime("%Y-%m-%d") in s["weekDays"]


def test_complete_persists_across_instances(tmp_path):
    store = JsonStore(tmp_path)
    StatsService(store).complete(25)
    assert StatsService(store).get()["tomato"] == 1


def test_streak_resets_after_gap(tmp_path):
    store = JsonStore(tmp_path)
    old_date = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
    store.write("stats", {
        "schemaVersion": 1, "date": old_date,
        "tomato": 5, "minutes": 100, "streak": 3, "weekDays": [],
    })
    s = StatsService(store).get()
    assert s["streak"] == 0
    assert s["tomato"] == 0  # 跨天归零


def test_streak_continues_from_yesterday(tmp_path):
    store = JsonStore(tmp_path)
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    store.write("stats", {
        "schemaVersion": 1, "date": yesterday,
        "tomato": 3, "minutes": 60, "streak": 2, "weekDays": [],
    })
    s = StatsService(store).get()
    assert s["streak"] == 2
    assert s["tomato"] == 0  # 今日番茄归零
