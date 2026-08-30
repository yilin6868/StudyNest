"""每日学习历史：记录每天番茄数/时长，用于「我的」板块回顾。"""
from datetime import datetime

from .store import JsonStore

SCHEMA_VERSION = 1


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default() -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "days": {}}


class HistoryService:
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self) -> dict:
        data = self.store.read("history", _default())
        days = data.get("days")
        if not isinstance(days, dict):
            days = {}
        data["days"] = days
        data["schemaVersion"] = SCHEMA_VERSION
        return data

    def record(self, minutes: int) -> dict:
        """完成一个番茄钟：今日番茄数 +1、时长累加。"""
        data = self.get()
        today = _today()
        day = dict(data["days"].get(today, {"tomato": 0, "minutes": 0}))
        day["tomato"] = int(day.get("tomato", 0)) + 1
        day["minutes"] = int(day.get("minutes", 0)) + int(minutes)
        data["days"][today] = day
        self.store.write("history", data)
        return data
