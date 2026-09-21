"""学习统计工具。"""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel

from ...repositories.study import StudyRepository
from ..context import ToolExecutionContext
from ..contracts import ContractModel, StudyStatsState
from ..permissions import PermissionLevel
from ..registry import ToolDefinition


class GetStudyStatsInput(ContractModel):
    scope: Literal["today", "week"] = "today"


def get_study_stats(
    _: BaseModel, context: ToolExecutionContext
) -> StudyStatsState:
    today = datetime.now(ZoneInfo(context.timezone_name)).date()
    stats = StudyRepository(context.db).get_stats(context.user_id, today=today)
    return StudyStatsState(
        today_tomato=stats["tomato"],
        today_minutes=stats["minutes"],
        streak=stats["streak"],
        week_study_days=len(stats["weekDays"]),
    )


STATS_TOOLS = (
    ToolDefinition(
        name="get_study_stats",
        description="查看当前用户今天和本周的学习统计",
        input_model=GetStudyStatsInput,
        output_model=StudyStatsState,
        side_effect=False,
        permission=PermissionLevel.AUTO,
        timeout_seconds=2,
        handler=get_study_stats,
    ),
)
