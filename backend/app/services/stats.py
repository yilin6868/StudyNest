"""统计与目标服务：统计从每日历史事实实时计算。"""

from datetime import date, timedelta

from ..core.time import now_local, today_local
from .history import HistoryService
from .store import JsonStore

SCHEMA_VERSION = 1


def _non_negative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def calculate_stats(days: dict, today: date) -> dict:
    """根据历史记录计算今日、本周和连续学习数据。"""
    studied_dates: set[date] = set()
    for raw_date, raw_day in days.items():
        if not isinstance(raw_date, str) or not isinstance(raw_day, dict):
            continue
        try:
            parsed = date.fromisoformat(raw_date)
        except ValueError:
            continue
        if parsed <= today and _non_negative_int(raw_day.get("tomato")) > 0:
            studied_dates.add(parsed)

    today_record = days.get(today.isoformat())
    if not isinstance(today_record, dict):
        today_record = {}

    monday = today - timedelta(days=today.weekday())
    week_days = sorted(
        studied.isoformat() for studied in studied_dates if monday <= studied <= today
    )

    cursor = today if today in studied_dates else today - timedelta(days=1)
    streak = 0
    while cursor in studied_dates:
        streak += 1
        cursor -= timedelta(days=1)

    return {
        "date": today.isoformat(),
        "tomato": _non_negative_int(today_record.get("tomato")),
        "minutes": _non_negative_int(today_record.get("minutes")),
        "streak": streak,
        "weekDays": week_days,
    }


class StatsService:
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self, *, today: date | None = None) -> dict:
        history = HistoryService(self.store).get()
        return calculate_stats(history["days"], today or today_local())

    def complete(self, minutes: int, session_id: str) -> dict:
        completed_at = now_local()
        HistoryService(self.store).record(
            minutes,
            session_id,
            completed_at=completed_at,
        )
        return self.get(today=completed_at.date())


class GoalService:
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self) -> str:
        data = self.store.read("goal", {"schemaVersion": SCHEMA_VERSION, "text": ""})
        return str(data.get("text", ""))

    def set(self, text: str) -> str:
        self.store.write("goal", {"schemaVersion": SCHEMA_VERSION, "text": text.strip()})
        return text.strip()
