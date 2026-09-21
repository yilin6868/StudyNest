"""统一应用时区，避免统计结果依赖服务器所在时区。"""

from datetime import date, datetime
from zoneinfo import ZoneInfo

from .config import settings


def app_timezone() -> ZoneInfo:
    return ZoneInfo(settings.app_timezone)


def now_local() -> datetime:
    return datetime.now(app_timezone())


def today_local() -> date:
    return now_local().date()
