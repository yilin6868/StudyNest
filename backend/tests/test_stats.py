from datetime import date, timedelta

from app.services.stats import StatsService, calculate_stats
from app.services.store import JsonStore


def _day(tomato: object = 1, minutes: object = 25) -> dict:
    return {"tomato": tomato, "minutes": minutes}


def test_initial_stats(tmp_path):
    stats = StatsService(JsonStore(tmp_path)).get(today=date(2026, 9, 8))
    assert stats == {
        "date": "2026-09-08",
        "tomato": 0,
        "minutes": 0,
        "streak": 0,
        "weekDays": [],
    }


def test_three_day_streak_including_today():
    today = date(2026, 9, 9)
    days = {
        (today - timedelta(days=2)).isoformat(): _day(),
        (today - timedelta(days=1)).isoformat(): _day(),
        today.isoformat(): _day(2, 50),
    }
    stats = calculate_stats(days, today)
    assert stats["streak"] == 3
    assert stats["tomato"] == 2
    assert stats["minutes"] == 50


def test_streak_kept_before_first_completion_today():
    today = date(2026, 9, 9)
    days = {
        (today - timedelta(days=2)).isoformat(): _day(),
        (today - timedelta(days=1)).isoformat(): _day(),
    }
    assert calculate_stats(days, today)["streak"] == 2


def test_streak_restarts_after_gap():
    today = date(2026, 9, 9)
    days = {
        (today - timedelta(days=2)).isoformat(): _day(),
        today.isoformat(): _day(),
    }
    assert calculate_stats(days, today)["streak"] == 1


def test_week_days_only_include_current_week_through_today():
    today = date(2026, 9, 9)  # Wednesday
    days = {
        "2026-09-06": _day(),  # previous Sunday
        "2026-09-07": _day(),
        "2026-09-08": _day(),
        "2026-09-10": _day(),  # future date is ignored
    }
    assert calculate_stats(days, today)["weekDays"] == ["2026-09-07", "2026-09-08"]


def test_week_resets_on_monday():
    today = date(2026, 9, 7)
    days = {"2026-09-06": _day(), "2026-09-07": _day()}
    assert calculate_stats(days, today)["weekDays"] == ["2026-09-07"]


def test_invalid_and_negative_records_are_ignored():
    today = date(2026, 9, 8)
    days = {
        "not-a-date": _day(),
        "2026-09-08": _day(-3, "bad"),
        "2026-09-09": _day(),
    }
    stats = calculate_stats(days, today)
    assert stats["tomato"] == 0
    assert stats["minutes"] == 0
    assert stats["streak"] == 0
    assert stats["weekDays"] == []


def test_complete_persists_and_is_idempotent(tmp_path):
    store = JsonStore(tmp_path)
    service = StatsService(store)
    first = service.complete(25, "session-one")
    second = service.complete(50, "session-one")
    assert first["tomato"] == 1
    assert first["minutes"] == 25
    assert second == first
    assert StatsService(store).get()["tomato"] == 1


def test_legacy_stats_snapshot_is_not_authoritative(tmp_path):
    store = JsonStore(tmp_path)
    store.write(
        "stats",
        {
            "schemaVersion": 1,
            "date": "2026-09-08",
            "tomato": 99,
            "minutes": 999,
            "streak": 99,
            "weekDays": ["2026-09-08"],
        },
    )
    stats = StatsService(store).get(today=date(2026, 9, 8))
    assert stats["tomato"] == 0
    assert stats["streak"] == 0
