"""今日目标工具。"""

from datetime import datetime
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from ...repositories.goals import GoalRepository
from ..context import ToolExecutionContext
from ..contracts import ContractModel, GoalState
from ..permissions import PermissionLevel
from ..registry import ToolDefinition
from .common import EmptyInput


class SetGoalInput(ContractModel):
    text: str = Field(min_length=1, max_length=60)


def _now(context: ToolExecutionContext) -> datetime:
    return datetime.now(ZoneInfo(context.timezone_name))


def get_today_goal(
    _: BaseModel, context: ToolExecutionContext
) -> GoalState:
    today = _now(context).date()
    return GoalState(
        date=today,
        text=GoalRepository(context.db).get(context.user_id, today),
    )


def set_today_goal(
    raw: BaseModel, context: ToolExecutionContext
) -> GoalState:
    args = SetGoalInput.model_validate(raw)
    now = _now(context)
    text = GoalRepository(context.db).set(
        context.user_id,
        now.date(),
        args.text.strip(),
        now=now,
        source="agent_tool",
    )
    return GoalState(date=now.date(), text=text)


GOAL_TOOLS = (
    ToolDefinition(
        name="get_today_goal",
        description="查看当前用户今天的学习目标",
        input_model=EmptyInput,
        output_model=GoalState,
        side_effect=False,
        permission=PermissionLevel.AUTO,
        timeout_seconds=2,
        handler=get_today_goal,
    ),
    ToolDefinition(
        name="set_today_goal",
        description="在用户明确要求时设置今天的学习目标",
        input_model=SetGoalInput,
        output_model=GoalState,
        side_effect=True,
        permission=PermissionLevel.EXPLICIT_INTENT,
        timeout_seconds=2,
        handler=set_today_goal,
    ),
)
