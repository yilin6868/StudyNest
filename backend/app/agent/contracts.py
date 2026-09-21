"""版本化 Agent 协议；模型输出和前端动作都必须经过严格校验。"""

from __future__ import annotations

import json
from datetime import date, datetime
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

PROTOCOL_VERSION = "1.2"
ACTION_PROTOCOL_VERSION = "1.1"


def _to_camel(value: str) -> str:
    first, *rest = value.split("_")
    return first + "".join(part.capitalize() for part in rest)


class ContractModel(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        populate_by_name=True,
        alias_generator=_to_camel,
        str_strip_whitespace=True,
    )


class GoalState(ContractModel):
    date: date
    text: str = Field(default="", max_length=60)


class FocusState(ContractModel):
    status: Literal[
        "idle", "running", "paused", "pending_settlement", "settlement_failed"
    ] = "idle"
    mode: Literal["focus", "break"] = "focus"
    remaining_seconds: int = Field(default=0, ge=0, le=43_200)

    @model_validator(mode="after")
    def idle_has_no_remaining_time(self) -> "FocusState":
        if self.status == "idle" and self.remaining_seconds != 0:
            raise ValueError("空闲状态的剩余时间必须为 0")
        if self.status in {"pending_settlement", "settlement_failed"}:
            if self.mode != "focus" or self.remaining_seconds != 0:
                raise ValueError("结算状态必须是剩余 0 秒的专注模式")
        return self


class StudyStatsState(ContractModel):
    today_tomato: int = Field(ge=0, le=10_000)
    today_minutes: int = Field(ge=0, le=600_000)
    streak: int = Field(ge=0, le=100_000)
    week_study_days: int = Field(ge=0, le=7)


class PreferenceState(ContractModel):
    buddy_gender: Literal["male", "female"] = "male"
    voice_enabled: bool = False


class AgentState(ContractModel):
    goal: GoalState
    focus: FocusState
    stats: StudyStatsState
    preferences: PreferenceState


class ConversationMessage(ContractModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=500)


class LearningMemory(ContractModel):
    category: Literal[
        "study_routine", "learning_preference", "companionship_style"
    ]
    content: str = Field(min_length=1, max_length=120)


class AgentInput(ContractModel):
    protocol_version: Literal["1.2"] = PROTOCOL_VERSION
    message: str = Field(min_length=1, max_length=200)
    conversation_summary: str = Field(default="", max_length=1_200)
    recent_messages: list[ConversationMessage] = Field(default_factory=list, max_length=8)
    memories: list[LearningMemory] = Field(default_factory=list, max_length=3)
    state: AgentState


class AgentChatRequest(ContractModel):
    protocol_version: Literal["1.2"] = PROTOCOL_VERSION
    session_id: str | None = Field(
        default=None,
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
    )
    message: str = Field(min_length=1, max_length=200)
    focus: FocusState = Field(default_factory=FocusState)


class PendingStartFocusAction(ContractModel):
    type: Literal["confirm_start_focus"] = "confirm_start_focus"
    duration_minutes: int = Field(ge=5, le=120)


class PendingPauseFocusAction(ContractModel):
    type: Literal["confirm_pause_focus"] = "confirm_pause_focus"


PendingFrontendAction = Annotated[
    PendingStartFocusAction | PendingPauseFocusAction,
    Field(discriminator="type"),
]


class ConfirmStartFocusAction(PendingStartFocusAction):
    confirmation_token: str = Field(min_length=32, max_length=128)
    expires_at: datetime


class ConfirmPauseFocusAction(PendingPauseFocusAction):
    confirmation_token: str = Field(min_length=32, max_length=128)
    expires_at: datetime


FrontendAction = Annotated[
    ConfirmStartFocusAction | ConfirmPauseFocusAction,
    Field(discriminator="type"),
]


class AgentResponse(ContractModel):
    protocol_version: Literal["1.2"] = PROTOCOL_VERSION
    request_id: str = Field(min_length=8, max_length=64, pattern=r"^[A-Za-z0-9_-]+$")
    session_id: str = Field(min_length=36, max_length=36)
    reply: str = Field(min_length=1, max_length=500)
    source: Literal["llm", "local"]
    response_mode: Literal["normal", "safety"] = "normal"
    actions: list[FrontendAction] = Field(default_factory=list, max_length=3)


class ModelToolCallDecision(ContractModel):
    kind: Literal["tool_call"] = "tool_call"
    tool_name: str = Field(min_length=1, max_length=64, pattern=r"^[a-z][a-z0-9_]*$")
    arguments: dict[str, Any] = Field(default_factory=dict)


class ModelFinalDecision(ContractModel):
    kind: Literal["final_response"] = "final_response"
    reply: str = Field(min_length=1, max_length=500)
    actions: list[PendingFrontendAction] = Field(default_factory=list, max_length=3)


ModelDecision = Annotated[
    ModelToolCallDecision | ModelFinalDecision,
    Field(discriminator="kind"),
]
model_decision_adapter = TypeAdapter(ModelDecision)


class ToolError(ContractModel):
    code: Literal[
        "TOOL_NOT_FOUND",
        "TOOL_INVALID_ARGUMENTS",
        "TOOL_PERMISSION_DENIED",
        "TOOL_TIMEOUT",
        "TOOL_EXECUTION_FAILED",
        "TOOL_INVALID_RESULT",
    ]
    message: str = Field(min_length=1, max_length=120)


class ToolCallResult(ContractModel):
    ok: bool
    permission: Literal["allow", "confirmation_required", "deny"]
    data: dict[str, Any] | None = None
    error: ToolError | None = None

    @model_validator(mode="after")
    def result_shape_matches_status(self) -> "ToolCallResult":
        if self.ok and self.error is not None:
            raise ValueError("成功结果不能包含错误")
        if self.ok and self.data is None:
            raise ValueError("成功结果必须包含数据")
        if not self.ok and self.error is None:
            raise ValueError("失败结果必须包含错误")
        if not self.ok and self.data is not None:
            raise ValueError("失败结果不能包含数据")
        return self


class ModelToolHistoryItem(ContractModel):
    tool_name: str = Field(min_length=1, max_length=64)
    arguments: dict[str, Any]
    result: ToolCallResult


class ResolveAgentActionRequest(ContractModel):
    protocol_version: Literal["1.1"] = ACTION_PROTOCOL_VERSION
    confirmation_token: str = Field(min_length=32, max_length=128)
    decision: Literal["confirm", "reject"]


class StartFocusAction(ContractModel):
    type: Literal["start_focus"] = "start_focus"
    duration_minutes: int = Field(ge=5, le=120)


class PauseFocusAction(ContractModel):
    type: Literal["pause_focus"] = "pause_focus"


ResolvedFrontendAction = Annotated[
    StartFocusAction | PauseFocusAction,
    Field(discriminator="type"),
]


class ResolveAgentActionResponse(ContractModel):
    accepted: bool
    action: ResolvedFrontendAction | None = None
    message: str = Field(min_length=1, max_length=120)

    @model_validator(mode="after")
    def accepted_has_an_action(self) -> "ResolveAgentActionResponse":
        if self.accepted != (self.action is not None):
            raise ValueError("确认结果与动作不一致")
        return self


class FocusSummaryRequest(ContractModel):
    session_id: str = Field(
        min_length=36,
        max_length=36,
        pattern=r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89aAbB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}$",
    )


class FocusSummaryResponse(ContractModel):
    session_id: str
    reply: str = Field(min_length=1, max_length=500)
    source: Literal["llm", "local"]


def parse_model_decision(raw: str | dict[str, Any]) -> ModelDecision:
    """只解析和校验单次模型决定，不执行 Agent 循环或工具。"""
    value = json.loads(raw) if isinstance(raw, str) else raw
    return model_decision_adapter.validate_python(value)


def safe_fallback_response(
    request_id: str,
    reply: str,
    *,
    session_id: str,
    response_mode: Literal["normal", "safety"] = "normal",
) -> AgentResponse:
    return AgentResponse(
        request_id=request_id,
        session_id=session_id,
        reply=reply,
        source="local",
        response_mode=response_mode,
        actions=[],
    )


def final_response_from_model(
    raw: str | dict[str, Any],
    *,
    request_id: str,
    session_id: str,
    fallback_reply: str,
) -> AgentResponse:
    """把模型最终回复转成公共协议；任何非法整包都安全降级。"""
    try:
        decision = parse_model_decision(raw)
    except (json.JSONDecodeError, ValidationError, TypeError):
        return safe_fallback_response(request_id, fallback_reply, session_id=session_id)
    if not isinstance(decision, ModelFinalDecision) or decision.actions:
        return safe_fallback_response(request_id, fallback_reply, session_id=session_id)
    return AgentResponse(
        request_id=request_id,
        session_id=session_id,
        reply=decision.reply,
        source="llm",
        actions=[],
    )
