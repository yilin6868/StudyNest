from datetime import datetime, timedelta, timezone
from unittest.mock import Mock
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.agent.context import (
    CallSource,
    IntentEvidence,
    ToolExecutionContext,
    VerifiedFocusCompletion,
    digest_arguments,
)
from app.agent.permissions import PermissionLevel, PermissionOutcome, ToolPermissionPolicy
from app.agent.tools.goals import SetGoalInput


def _context(**changes) -> ToolExecutionContext:
    values = {
        "user_id": "user-1",
        "request_id": "request_123",
        "source": CallSource.AGENT,
        "db": Mock(),
    }
    values.update(changes)
    return ToolExecutionContext(**values)


def _intent(tool_name: str, arguments: dict) -> dict[str, IntentEvidence]:
    return {
        tool_name: IntentEvidence(
            user_id="user-1",
            request_id="request_123",
            tool_name=tool_name,
            arguments_digest=digest_arguments(arguments),
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
        )
    }


def test_read_only_permission_is_automatic():
    decision = ToolPermissionPolicy().evaluate(
        tool_name="get_today_goal",
        level=PermissionLevel.AUTO,
        context=_context(),
    )
    assert decision.outcome == PermissionOutcome.ALLOW


def test_explicit_intent_is_server_context_not_model_arguments():
    denied = ToolPermissionPolicy().evaluate(
        tool_name="set_today_goal",
        level=PermissionLevel.EXPLICIT_INTENT,
        context=_context(),
    )
    allowed = ToolPermissionPolicy().evaluate(
        tool_name="set_today_goal",
        level=PermissionLevel.EXPLICIT_INTENT,
        context=_context(intent_evidence=_intent("set_today_goal", {"text": "学习"})),
        arguments={"text": "学习"},
    )

    assert denied.outcome == PermissionOutcome.DENY
    assert allowed.outcome == PermissionOutcome.ALLOW
    with pytest.raises(ValidationError):
        SetGoalInput.model_validate({"text": "学习", "userConfirmed": True})


def test_confirmation_required_never_becomes_direct_allow():
    decision = ToolPermissionPolicy().evaluate(
        tool_name="request_start_focus",
        level=PermissionLevel.CONFIRMATION_REQUIRED,
        context=_context(),
    )
    assert decision.outcome == PermissionOutcome.CONFIRMATION_REQUIRED


def test_trusted_system_tool_requires_source_and_verified_evidence():
    policy = ToolPermissionPolicy()
    no_evidence = policy.evaluate(
        tool_name="complete_focus",
        level=PermissionLevel.TRUSTED_SYSTEM_ONLY,
        context=_context(source=CallSource.SYSTEM),
    )
    forged_agent = policy.evaluate(
        tool_name="complete_focus",
        level=PermissionLevel.TRUSTED_SYSTEM_ONLY,
        context=_context(
            verified_focus_completion=VerifiedFocusCompletion(
                session_id=uuid4(), minutes=25
            )
        ),
    )

    assert no_evidence.outcome == PermissionOutcome.DENY
    assert forged_agent.outcome == PermissionOutcome.DENY
