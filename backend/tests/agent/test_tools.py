from datetime import datetime, timedelta, timezone
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.agent import build_default_registry
from app.agent.context import (
    CallSource,
    IntentEvidence,
    ToolExecutionContext,
    VerifiedFocusCompletion,
    digest_arguments,
)
from app.agent.contracts import FocusState
from app.repositories.goals import GoalRepository
from app.repositories.preferences import PreferenceRepository
from app.repositories.study import StudyRepository


EXPECTED_TOOLS = {
    "get_today_goal",
    "set_today_goal",
    "get_focus_state",
    "request_start_focus",
    "request_pause_focus",
    "complete_focus",
    "get_study_stats",
    "update_preference",
    "save_learning_memory",
}


def _context(db_session, user, **changes):
    values = {
        "user_id": user.id,
        "request_id": f"request_{uuid4().hex}",
        "source": CallSource.AGENT,
        "db": db_session,
        "timezone_name": user.timezone,
    }
    values.update(changes)
    return ToolExecutionContext(**values)


def _intent_context(db_session, user, tool_name: str, arguments: dict, **changes):
    request_id = f"request_{uuid4().hex}"
    evidence = IntentEvidence(
        user_id=user.id,
        request_id=request_id,
        tool_name=tool_name,
        arguments_digest=digest_arguments(arguments),
        expires_at=datetime.now(timezone.utc) + timedelta(minutes=1),
    )
    return _context(
        db_session,
        user,
        request_id=request_id,
        intent_evidence={tool_name: evidence},
        **changes,
    )


def test_default_registry_contains_p1_c_memory_tool():
    assert set(build_default_registry().names()) == EXPECTED_TOOLS


def test_goal_tool_requires_intent_and_uses_current_user(db_session, user_factory):
    user = user_factory()
    other = user_factory()
    registry = build_default_registry()

    denied = registry.execute(
        "set_today_goal", {"text": "学习数学"}, _context(db_session, user)
    )
    allowed = registry.execute(
        "set_today_goal",
        {"text": "学习数学"},
        _intent_context(db_session, user, "set_today_goal", {"text": "学习数学"}),
    )
    forged = registry.execute(
        "set_today_goal",
        {"text": "越权", "userId": other.id},
        _intent_context(db_session, user, "set_today_goal", {"text": "越权"}),
    )

    today = datetime.now(ZoneInfo(user.timezone)).date()
    assert denied.error.code == "TOOL_PERMISSION_DENIED"
    assert allowed.ok is True
    assert forged.error.code == "TOOL_INVALID_ARGUMENTS"
    assert GoalRepository(db_session).get(user.id, today) == "学习数学"
    assert GoalRepository(db_session).get(other.id, today) == ""


def test_focus_requests_only_return_actions(db_session, user_factory):
    user = user_factory()
    registry = build_default_registry()
    running_context = _context(
        db_session,
        user,
        focus_state=FocusState(status="running", remaining_seconds=600),
    )

    state = registry.execute("get_focus_state", {}, running_context)
    start = registry.execute(
        "request_start_focus", {"durationMinutes": 25}, _context(db_session, user)
    )
    pause_denied = registry.execute("request_pause_focus", {}, running_context)
    pause = registry.execute(
        "request_pause_focus",
        {},
        _intent_context(
            db_session,
            user,
            "request_pause_focus",
            {},
            focus_state=FocusState(status="running", remaining_seconds=600),
        ),
    )

    assert state.data["status"] == "running"
    assert start.permission == "confirmation_required"
    assert start.data["action"] == {
        "type": "confirm_start_focus",
        "durationMinutes": 25,
    }
    assert pause_denied.error.code == "TOOL_PERMISSION_DENIED"
    assert pause.data["action"] == {"type": "confirm_pause_focus"}
    assert StudyRepository(db_session).get_days(user.id) == {}


def test_preference_tool_requires_intent_and_persists_whitelist(db_session, user_factory):
    user = user_factory()
    registry = build_default_registry()

    denied = registry.execute(
        "update_preference", {"voiceEnabled": True}, _context(db_session, user)
    )
    allowed = registry.execute(
        "update_preference",
        {"buddyGender": "female", "voiceEnabled": True},
        _intent_context(
            db_session,
            user,
            "update_preference",
            {"buddyGender": "female", "voiceEnabled": True},
        ),
    )

    assert denied.error.code == "TOOL_PERMISSION_DENIED"
    assert allowed.data == {"buddyGender": "female", "voiceEnabled": True}
    assert PreferenceRepository(db_session).get(user.id) == {
        "buddy_gender": "female",
        "voice_enabled": True,
    }


def test_complete_focus_is_system_only_and_idempotent(db_session, user_factory):
    user = user_factory()
    registry = build_default_registry()
    session_id = uuid4()
    arguments = {"sessionId": str(session_id), "minutes": 25}

    denied = registry.execute(
        "complete_focus",
        arguments,
        _context(
            db_session,
            user,
            verified_focus_completion=VerifiedFocusCompletion(session_id, 25),
        ),
    )
    trusted = _context(
        db_session,
        user,
        source=CallSource.SYSTEM,
        verified_focus_completion=VerifiedFocusCompletion(session_id, 25),
    )
    first = registry.execute("complete_focus", arguments, trusted)
    repeated_in_request = registry.execute("complete_focus", arguments, trusted)
    repeated_new_request = registry.execute(
        "complete_focus",
        arguments,
        _context(
            db_session,
            user,
            source=CallSource.SYSTEM,
            verified_focus_completion=VerifiedFocusCompletion(session_id, 25),
        ),
    )

    assert denied.error.code == "TOOL_PERMISSION_DENIED"
    assert first.data["created"] is True
    assert repeated_in_request.error.code == "TOOL_PERMISSION_DENIED"
    assert repeated_new_request.data["created"] is False
    days = StudyRepository(db_session).get_days(user.id)
    assert sum(day["tomato"] for day in days.values()) == 1
    assert sum(day["minutes"] for day in days.values()) == 25


def test_complete_focus_rejects_bad_uuid_or_mismatched_evidence(db_session, user_factory):
    user = user_factory()
    registry = build_default_registry()
    evidence_id = uuid4()
    context = _context(
        db_session,
        user,
        source=CallSource.SYSTEM,
        verified_focus_completion=VerifiedFocusCompletion(evidence_id, 25),
    )

    bad_uuid = registry.execute(
        "complete_focus", {"sessionId": "not-a-uuid", "minutes": 25}, context
    )
    mismatch = registry.execute(
        "complete_focus",
        {"sessionId": str(uuid4()), "minutes": 25},
        context,
    )

    assert bad_uuid.error.code == "TOOL_INVALID_ARGUMENTS"
    assert mismatch.error.code == "TOOL_EXECUTION_FAILED"
    assert StudyRepository(db_session).get_days(user.id) == {}
