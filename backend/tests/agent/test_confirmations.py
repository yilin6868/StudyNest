from datetime import datetime, timedelta, timezone

import pytest

from app.agent.confirmations import ConfirmationService
from app.agent.contracts import PendingPauseFocusAction, PendingStartFocusAction
from app.repositories.agent_actions import ActionResolutionError, AgentActionRepository


def test_reject_consumes_token_without_returning_an_action(db_session, user_factory):
    user = user_factory()
    service = ConfirmationService()
    issued = service.issue(
        db_session,
        user_id=user.id,
        request_id="req_reject_123",
        action=PendingPauseFocusAction(),
    )
    db_session.commit()
    result = service.resolve(
        db_session,
        user_id=user.id,
        token=issued.confirmation_token,
        decision="reject",
    )
    assert result.accepted is False
    assert result.action is None
    with pytest.raises(ActionResolutionError):
        service.resolve(
            db_session,
            user_id=user.id,
            token=issued.confirmation_token,
            decision="confirm",
        )


def test_confirmation_is_bound_to_current_user(db_session, user_factory):
    owner = user_factory()
    other = user_factory()
    service = ConfirmationService()
    issued = service.issue(
        db_session,
        user_id=owner.id,
        request_id="req_owner_123",
        action=PendingStartFocusAction(duration_minutes=25),
    )
    db_session.commit()
    with pytest.raises(ActionResolutionError) as error:
        service.resolve(
            db_session,
            user_id=other.id,
            token=issued.confirmation_token,
            decision="confirm",
        )
    assert error.value.status_code == 404


def test_expired_confirmation_cannot_be_used(db_session, user_factory):
    user = user_factory()
    repository = AgentActionRepository(db_session)
    past = datetime.now(timezone.utc) - timedelta(minutes=2)
    issued = repository.issue(
        user_id=user.id,
        request_id="req_expired_123",
        action_type="start_focus",
        arguments={"durationMinutes": 25},
        ttl_seconds=30,
        now=past,
    )
    db_session.commit()
    with pytest.raises(ActionResolutionError) as error:
        repository.resolve(
            user_id=user.id,
            token=issued.token,
            decision="confirm",
            now=datetime.now(timezone.utc),
        )
    assert error.value.code == "ACTION_EXPIRED"
