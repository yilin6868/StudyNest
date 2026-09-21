import json

import pytest
from pydantic import ValidationError

from app.agent.contracts import (
    AgentInput,
    AgentResponse,
    FocusState,
    ModelFinalDecision,
    ModelToolCallDecision,
    ToolCallResult,
    ToolError,
    final_response_from_model,
    parse_model_decision,
    safe_fallback_response,
)


def _agent_input() -> dict:
    return {
        "protocolVersion": "1.2",
        "message": "我想开始学习了",
        "conversationSummary": "",
        "state": {
            "goal": {"date": "2026-09-09", "text": "背 50 个单词"},
            "focus": {"status": "idle", "mode": "focus", "remainingSeconds": 0},
            "stats": {
                "todayTomato": 2,
                "todayMinutes": 50,
                "streak": 3,
                "weekStudyDays": 2,
            },
            "preferences": {"buddyGender": "male", "voiceEnabled": False},
        },
    }


def test_agent_input_is_versioned_and_serializes_with_frontend_names():
    value = AgentInput.model_validate(_agent_input())
    result = value.model_dump(mode="json", by_alias=True)

    assert result["protocolVersion"] == "1.2"
    assert result["state"]["focus"]["remainingSeconds"] == 0


@pytest.mark.parametrize(
    "change",
    [
        lambda value: value.update({"protocolVersion": "2.0"}),
        lambda value: value.update({"unexpected": True}),
        lambda value: value["state"]["goal"].update({"userId": "someone-else"}),
    ],
)
def test_agent_input_rejects_unknown_versions_and_fields(change):
    value = _agent_input()
    change(value)

    with pytest.raises(ValidationError):
        AgentInput.model_validate(value)


def test_focus_state_rejects_impossible_idle_snapshot():
    with pytest.raises(ValidationError):
        FocusState(status="idle", remaining_seconds=10)


def test_model_decision_has_an_explicit_discriminator():
    call = parse_model_decision(
        '{"kind":"tool_call","toolName":"get_today_goal","arguments":{}}'
    )
    final = parse_model_decision(
        {"kind": "final_response", "reply": "继续加油", "actions": []}
    )

    assert isinstance(call, ModelToolCallDecision)
    assert isinstance(final, ModelFinalDecision)


@pytest.mark.parametrize(
    "raw",
    [
        "not json",
        {"kind": "unknown", "reply": "no"},
        {
            "kind": "final_response",
            "reply": "no",
            "actions": [{"type": "run_shell"}],
        },
    ],
)
def test_model_decision_rejects_malformed_or_unknown_output(raw):
    with pytest.raises((json.JSONDecodeError, ValidationError)):
        parse_model_decision(raw)


def test_agent_response_limits_actions_and_rejects_unknown_fields():
    action = {"type": "confirm_pause_focus"}
    with pytest.raises(ValidationError):
        AgentResponse(
            request_id="request_123",
            session_id="00000000-0000-4000-8000-000000000001",
            reply="暂停吗？",
            source="llm",
            actions=[action, action, action, action],
        )
    with pytest.raises(ValidationError):
        AgentResponse.model_validate(
            {
                "requestId": "request_123",
                "sessionId": "00000000-0000-4000-8000-000000000001",
                "reply": "暂停吗？",
                "source": "llm",
                "actions": [],
                "debug": "secret",
            }
        )


def test_safe_fallback_contains_only_local_text_and_no_actions():
    result = safe_fallback_response(
        "request_123",
        "我这边刚刚走神了，我们继续聊聊吧。",
        session_id="00000000-0000-4000-8000-000000000001",
    )

    assert result.source == "local"
    assert result.actions == []


def test_invalid_model_output_automatically_becomes_safe_fallback():
    fallback = final_response_from_model(
        '{"kind":"final_response","reply":"ok","actions":[{"type":"run_shell"}]}',
        request_id="request_123",
        session_id="00000000-0000-4000-8000-000000000001",
        fallback_reply="我们继续聊聊吧。",
    )
    valid = final_response_from_model(
        {"kind": "final_response", "reply": "继续学习", "actions": []},
        request_id="request_456",
        session_id="00000000-0000-4000-8000-000000000001",
        fallback_reply="fallback",
    )

    assert fallback.source == "local"
    assert fallback.actions == []
    assert valid.source == "llm"
    assert valid.reply == "继续学习"


def test_tool_result_requires_an_error_on_failure():
    valid = ToolCallResult(
        ok=False,
        permission="deny",
        error=ToolError(code="TOOL_NOT_FOUND", message="未找到"),
    )
    assert valid.data is None
    with pytest.raises(ValidationError):
        ToolCallResult(ok=False, permission="deny")
    with pytest.raises(ValidationError):
        ToolCallResult(ok=True, permission="allow", data=None)
