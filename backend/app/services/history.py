"""每日学习事实：保存历史，并用 sessionId 防止重复结算。"""

from datetime import datetime

from ..core.time import now_local
from .store import JsonStore

SCHEMA_VERSION = 2


def _default() -> dict:
    return {"schemaVersion": SCHEMA_VERSION, "days": {}, "completedSessions": {}}


def _non_negative_int(value: object) -> int:
    try:
        return max(0, int(value))
    except (TypeError, ValueError):
        return 0


def _normalize(data: dict) -> dict:
    days = data.get("days")
    sessions = data.get("completedSessions")
    return {
        **data,
        "schemaVersion": SCHEMA_VERSION,
        "days": days if isinstance(days, dict) else {},
        "completedSessions": sessions if isinstance(sessions, dict) else {},
    }


class HistoryService:
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self) -> dict:
        return _normalize(self.store.read("history", _default()))

    def record(
        self,
        minutes: int,
        session_id: str,
        *,
        completed_at: datetime | None = None,
    ) -> tuple[dict, bool]:
        """原子记录一轮专注；已存在的 sessionId 返回原数据。"""
        completed_at = completed_at or now_local()
        day_key = completed_at.date().isoformat()
        created = False

        def apply(raw: dict) -> dict:
            nonlocal created
            data = _normalize(raw)
            if session_id in data["completedSessions"]:
                return data

            raw_day = data["days"].get(day_key)
            day = dict(raw_day) if isinstance(raw_day, dict) else {}
            day["tomato"] = _non_negative_int(day.get("tomato")) + 1
            day["minutes"] = _non_negative_int(day.get("minutes")) + int(minutes)
            data["days"][day_key] = day
            data["completedSessions"][session_id] = {
                "date": day_key,
                "minutes": int(minutes),
                "completedAt": completed_at.isoformat(),
            }
            created = True
            return data

        data = self.store.update("history", _default(), apply)
        return data, created
