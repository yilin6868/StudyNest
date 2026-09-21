"""专注状态、待确认动作和可信结算工具。"""

from datetime import datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from pydantic import BaseModel, Field

from ...repositories.study import StudyRepository
from ..context import ToolExecutionContext
from ..contracts import (
    ContractModel,
    FocusState,
    PendingPauseFocusAction,
    PendingStartFocusAction,
    StudyStatsState,
)
from ..errors import ToolHandlerError
from ..permissions import PermissionLevel
from ..registry import ToolDefinition
from .common import EmptyInput


class RequestStartFocusInput(ContractModel):
    duration_minutes: int = Field(default=25, ge=5, le=120)


class StartFocusRequestResult(ContractModel):
    action: PendingStartFocusAction


class PauseFocusRequestResult(ContractModel):
    action: PendingPauseFocusAction


class CompleteFocusInput(ContractModel):
    session_id: UUID
    minutes: int = Field(ge=1, le=600)


class CompleteFocusResult(ContractModel):
    created: bool
    stats: StudyStatsState


def get_focus_state(_: BaseModel, context: ToolExecutionContext) -> FocusState:
    return context.focus_state


def request_start_focus(
    raw: BaseModel, context: ToolExecutionContext
) -> StartFocusRequestResult:
    args = RequestStartFocusInput.model_validate(raw)
    if context.focus_state.status != "idle":
        raise ToolHandlerError("当前已有专注计时，不能重复开始")
    return StartFocusRequestResult(
        action=PendingStartFocusAction(duration_minutes=args.duration_minutes)
    )


def request_pause_focus(
    _: BaseModel, context: ToolExecutionContext
) -> PauseFocusRequestResult:
    if context.focus_state.status != "running":
        raise ToolHandlerError("当前没有正在进行的专注计时")
    return PauseFocusRequestResult(action=PendingPauseFocusAction())


def complete_focus(
    raw: BaseModel, context: ToolExecutionContext
) -> CompleteFocusResult:
    args = CompleteFocusInput.model_validate(raw)
    evidence = context.verified_focus_completion
    if (
        evidence is None
        or evidence.session_id != args.session_id
        or evidence.minutes != args.minutes
    ):
        raise ToolHandlerError("可信计时证据与请求不一致")
    completed_at = datetime.now(ZoneInfo(context.timezone_name))
    repository = StudyRepository(context.db)
    created = repository.complete(
        user_id=context.user_id,
        client_session_id=str(args.session_id),
        minutes=args.minutes,
        completed_at=completed_at,
        source="trusted_agent_tool",
    )
    stats = repository.get_stats(context.user_id, today=completed_at.date())
    return CompleteFocusResult(
        created=created,
        stats=StudyStatsState(
            today_tomato=stats["tomato"],
            today_minutes=stats["minutes"],
            streak=stats["streak"],
            week_study_days=len(stats["weekDays"]),
        ),
    )


FOCUS_TOOLS = (
    ToolDefinition(
        name="get_focus_state",
        description="查看本次请求携带的客户端专注状态摘要",
        input_model=EmptyInput,
        output_model=FocusState,
        side_effect=False,
        permission=PermissionLevel.AUTO,
        timeout_seconds=1,
        handler=get_focus_state,
    ),
    ToolDefinition(
        name="request_start_focus",
        description="生成开始专注的前端确认动作，不直接开始计时",
        input_model=RequestStartFocusInput,
        output_model=StartFocusRequestResult,
        side_effect=False,
        permission=PermissionLevel.CONFIRMATION_REQUIRED,
        timeout_seconds=1,
        handler=request_start_focus,
    ),
    ToolDefinition(
        name="request_pause_focus",
        description="在用户明确要求时生成暂停专注确认动作",
        input_model=EmptyInput,
        output_model=PauseFocusRequestResult,
        side_effect=False,
        permission=PermissionLevel.EXPLICIT_INTENT,
        timeout_seconds=1,
        handler=request_pause_focus,
    ),
    ToolDefinition(
        name="complete_focus",
        description="仅由可信计时完成流程幂等结算一次专注",
        input_model=CompleteFocusInput,
        output_model=CompleteFocusResult,
        side_effect=True,
        permission=PermissionLevel.TRUSTED_SYSTEM_ONLY,
        timeout_seconds=3,
        handler=complete_focus,
    ),
)
