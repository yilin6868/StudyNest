from datetime import datetime
import asyncio
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy import select

from app.agent.confirmations import ConfirmationService
from app.agent.contracts import (
    FocusState,
    ModelFinalDecision,
    ModelToolCallDecision,
    PendingStartFocusAction,
)
from app.agent.runtime import AgentRuntime
from app.db.models import AgentActionConfirmation
from app.repositories.agent_actions import ActionResolutionError
from app.repositories.goals import GoalRepository


class FakeModel:
    def __init__(self, decisions, *, available=True, summary="完成得很棒"):
        self.decisions = list(decisions)
        self.available = available
        self.summary = summary
        self.tools = []

    async def decide(self, _input, tools, _history, *, timeout_seconds):
        self.tools = tools
        return self.decisions.pop(0)

    async def summarize(self, _facts, *, timeout_seconds):
        return self.summary


class SlowModel(FakeModel):
    async def decide(self, _input, tools, _history, *, timeout_seconds):
        await asyncio.sleep(0.05)
        return ModelFinalDecision(reply="太慢了", actions=[])


@pytest.mark.asyncio
async def test_runtime_executes_bound_goal_tool(db_session, user_factory):
    user = user_factory()
    model = FakeModel(
        [
            ModelToolCallDecision(
                tool_name="set_today_goal", arguments={"text": "背 50 个单词"}
            ),
            ModelFinalDecision(reply="目标已经保存。", actions=[]),
        ]
    )
    response = await AgentRuntime(model=model).chat(
        db_session,
        user,
        message="把今天目标设为背 50 个单词",
        focus=FocusState(),
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    assert response.source == "llm"
    assert GoalRepository(db_session).get(user.id, today) == "背 50 个单词"
    assert all(tool["name"] != "complete_focus" for tool in model.tools)


@pytest.mark.asyncio
async def test_runtime_rejects_model_arguments_that_differ_from_user_words(
    db_session, user_factory
):
    user = user_factory()
    model = FakeModel(
        [
            ModelToolCallDecision(
                tool_name="set_today_goal", arguments={"text": "学习数学"}
            ),
            ModelFinalDecision(reply="我没有修改目标。", actions=[]),
        ]
    )
    await AgentRuntime(model=model).chat(
        db_session,
        user,
        message="把今天目标设为背单词",
        focus=FocusState(),
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    assert GoalRepository(db_session).get(user.id, today) == ""


@pytest.mark.asyncio
async def test_runtime_issues_one_time_frontend_confirmation(db_session, user_factory):
    user = user_factory()
    pending = PendingStartFocusAction(duration_minutes=30)
    model = FakeModel(
        [
            ModelToolCallDecision(
                tool_name="request_start_focus", arguments={"durationMinutes": 30}
            ),
            ModelFinalDecision(reply="准备开始吗？", actions=[pending]),
        ]
    )
    response = await AgentRuntime(model=model).chat(
        db_session, user, message="开始专注吧", focus=FocusState()
    )
    assert response.actions[0].type == "confirm_start_focus"
    token = response.actions[0].confirmation_token
    record = db_session.scalar(select(AgentActionConfirmation))
    assert token not in record.token_digest
    assert token not in record.arguments_json

    service = ConfirmationService()
    resolved = service.resolve(
        db_session, user_id=user.id, token=token, decision="confirm"
    )
    assert resolved.accepted is True
    assert resolved.action.duration_minutes == 30
    with pytest.raises(ActionResolutionError):
        service.resolve(db_session, user_id=user.id, token=token, decision="confirm")


@pytest.mark.asyncio
async def test_unavailable_model_returns_legal_local_response(db_session, user_factory):
    user = user_factory()
    response = await AgentRuntime(model=FakeModel([], available=False)).chat(
        db_session, user, message="你好", focus=FocusState()
    )
    assert response.source == "local"
    assert response.actions == []


@pytest.mark.asyncio
async def test_model_timeout_safely_falls_back(
    db_session, user_factory, monkeypatch
):
    user = user_factory()
    monkeypatch.setattr("app.agent.runtime.settings.agent_model_timeout_seconds", 0.001)
    response = await AgentRuntime(model=SlowModel([])).chat(
        db_session, user, message="你好", focus=FocusState()
    )
    assert response.source == "local"
    assert response.actions == []


@pytest.mark.asyncio
async def test_duplicate_tool_call_stops_without_repeating_side_effect(
    db_session, user_factory
):
    user = user_factory()
    call = ModelToolCallDecision(
        tool_name="set_today_goal", arguments={"text": "阅读一章"}
    )
    response = await AgentRuntime(model=FakeModel([call, call])).chat(
        db_session,
        user,
        message="把今天目标设为阅读一章",
        focus=FocusState(),
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    assert response.source == "local"
    assert GoalRepository(db_session).get(user.id, today) == "阅读一章"


@pytest.mark.asyncio
async def test_saved_goal_is_reported_accurately_if_later_model_call_fails(
    db_session, user_factory
):
    user = user_factory()
    model = FakeModel(
        [
            ModelToolCallDecision(
                tool_name="set_today_goal", arguments={"text": "复习英语"}
            )
        ]
    )
    response = await AgentRuntime(model=model).chat(
        db_session,
        user,
        message="把今天目标设为复习英语",
        focus=FocusState(),
    )
    today = datetime.now(ZoneInfo(user.timezone)).date()
    assert GoalRepository(db_session).get(user.id, today) == "复习英语"
    assert response.source == "local"
    assert "已经保存" in response.reply


@pytest.mark.asyncio
async def test_model_cannot_invent_an_executable_action(db_session, user_factory):
    user = user_factory()
    invented = PendingStartFocusAction(duration_minutes=25)
    response = await AgentRuntime(
        model=FakeModel(
            [ModelFinalDecision(reply="已经准备好了", actions=[invented])]
        )
    ).chat(db_session, user, message="你好", focus=FocusState())
    assert response.source == "local"
    assert response.actions == []
