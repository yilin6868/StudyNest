"""统计与目标服务：基于结构化 JSON 文件持久化，进程重启可恢复。"""
from datetime import date, datetime, timedelta

from ..core.config import settings
from .store import JsonStore

SCHEMA_VERSION = 1


def _today() -> str:
    return datetime.now().strftime("%Y-%m-%d")


def _default_stats() -> dict:
    return {
        "schemaVersion": SCHEMA_VERSION,
        "date": _today(),
        "tomato": 0,
        "minutes": 0,
        "streak": 0,
        "weekDays": [],
    }


class StatsService:
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self) -> dict:
        raw = self.store.read("stats", _default_stats())
        today = _today()

        # 跨天：番茄数/分钟归零，streak 按"昨天是否有记录"延续
        if raw.get("date") != today:
            yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
            streak = int(raw.get("streak", 0)) if raw.get("date") == yesterday else 0
            raw = {**_default_stats(), "date": today, "streak": streak}

        # 字段补齐（兼容旧数据 / 缺字段）
        for k, v in _default_stats().items():
            raw.setdefault(k, v)
        raw["schemaVersion"] = SCHEMA_VERSION
        return raw

    def save(self, stats: dict) -> dict:
        stats["schemaVersion"] = SCHEMA_VERSION
        self.store.write("stats", stats)
        return stats

    def complete(self, minutes: int = 25) -> dict:
        stats = self.get()
        stats["tomato"] = int(stats.get("tomato", 0)) + 1
        stats["minutes"] = int(stats.get("minutes", 0)) + int(minutes)
        stats["streak"] = max(1, int(stats.get("streak", 0)))

        week_days = {d for d in stats.get("weekDays", []) if self._in_this_week(d)}
        week_days.add(_today())
        stats["weekDays"] = sorted(week_days)
        return self.save(stats)

    @staticmethod
    def _in_this_week(d: str) -> bool:
        """周一为一周开始。"""
        try:
            dt = datetime.strptime(d, "%Y-%m-%d").date()
        except ValueError:
            return False
        today = date.today()
        monday = today - timedelta(days=today.weekday())
        sunday = monday + timedelta(days=6)
        return monday <= dt <= sunday


class GoalService:
    def __init__(self, store: JsonStore):
        self.store = store

    def get(self) -> str:
        data = self.store.read("goal", {"schemaVersion": SCHEMA_VERSION, "text": ""})
        return str(data.get("text", ""))

    def set(self, text: str) -> str:
        self.store.write("goal", {"schemaVersion": SCHEMA_VERSION, "text": text.strip()})
        return text.strip()
