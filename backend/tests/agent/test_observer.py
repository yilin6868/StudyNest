from datetime import datetime
from zoneinfo import ZoneInfo

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select

from app.agent.contracts import FocusState
from app.agent.errors import AgentContextError
from app.agent.observer import StateObserver
from app.db.models import UserPreference
from app.repositories.goals import GoalRepository
from app.repositories.preferences import PreferenceRepository
from app.repositories.study import StudyRepository


def test_observer_returns_stable_defaults_without_writing(db_session, user_factory):
    user = user_factory()
    before = db_session.scalar(select(func.count()).select_from(UserPreference))

    result = StateObserver().build(db_session, user, message="今天学什么？")
    after = db_session.scalar(select(func.count()).select_from(UserPreference))

    assert result.state.goal.text == ""
    assert result.state.stats.today_tomato == 0
    assert result.state.preferences.buddy_gender == "male"
    assert result.state.preferences.voice_enabled is False
    assert before == after


def test_observer_isolates_each_users_state(db_session, user_factory):
    first = user_factory()
    second = user_factory()
    now = datetime.now(ZoneInfo(first.timezone))
    GoalRepository(db_session).set(first.id, now.date(), "用户 A 的目标", now=now)
    StudyRepository(db_session).complete(
        user_id=first.id,
        client_session_id="10187b8c-e265-4a79-a6e4-1c83df79da29",
        minutes=25,
        completed_at=now,
    )
    PreferenceRepository(db_session).update(
        first.id, buddy_gender="female", voice_enabled=True, now=now
    )
    db_session.commit()

    first_state = StateObserver().build(db_session, first, message="状态")
    second_state = StateObserver().build(db_session, second, message="状态")

    assert first_state.state.goal.text == "用户 A 的目标"
    assert first_state.state.stats.today_minutes == 25
    assert first_state.state.preferences.voice_enabled is True
    assert second_state.state.goal.text == ""
    assert second_state.state.stats.today_minutes == 0
    assert second_state.state.preferences.voice_enabled is False


def test_observer_output_contains_no_identity_or_secret_fields(db_session, user_factory):
    user = user_factory()
    payload = StateObserver().build(db_session, user, message="看看状态").model_dump_json(
        by_alias=True
    )

    assert user.id not in payload
    assert user.username not in payload
    assert "password" not in payload.lower()
    assert "token" not in payload.lower()


def test_observer_rejects_invalid_focus_and_oversized_context(db_session, user_factory):
    user = user_factory()
    with pytest.raises(ValidationError):
        StateObserver().build(
            db_session,
            user,
            message="状态",
            focus_state={"status": "idle", "remainingSeconds": 100},
        )
    with pytest.raises(AgentContextError):
        StateObserver(max_bytes=512).build(db_session, user, message="学" * 200)


def test_observer_rejects_inactive_user(db_session, user_factory):
    user = user_factory(status="disabled")
    with pytest.raises(AgentContextError):
        StateObserver().build(db_session, user, message="状态")


def test_focus_snapshot_is_only_observed_not_used_as_fact(db_session, user_factory):
    user = user_factory()
    result = StateObserver().build(
        db_session,
        user,
        message="我在专注",
        focus_state=FocusState(status="running", remaining_seconds=600),
    )

    assert result.state.focus.status == "running"
    assert result.state.stats.today_tomato == 0
