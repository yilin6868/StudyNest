"""签发和兑现白名单前端动作。"""

from __future__ import annotations

from sqlalchemy.orm import Session

from ..core.config import settings
from ..repositories.agent_actions import AgentActionRepository
from ..repositories.agent_actions import ActionResolutionError
from .contracts import (
    ConfirmPauseFocusAction,
    ConfirmStartFocusAction,
    FrontendAction,
    PauseFocusAction,
    PendingFrontendAction,
    ResolveAgentActionResponse,
    StartFocusAction,
)


class ConfirmationService:
    def issue(
        self,
        db: Session,
        *,
        user_id: str,
        request_id: str,
        action: PendingFrontendAction,
    ) -> FrontendAction:
        if action.type == "confirm_start_focus":
            action_type = "start_focus"
            arguments = {"durationMinutes": action.duration_minutes}
        else:
            action_type = "pause_focus"
            arguments = {}
        issued = AgentActionRepository(db).issue(
            user_id=user_id,
            request_id=request_id,
            action_type=action_type,
            arguments=arguments,
            ttl_seconds=settings.agent_action_ttl_seconds,
        )
        if action_type == "start_focus":
            return ConfirmStartFocusAction(
                duration_minutes=arguments["durationMinutes"],
                confirmation_token=issued.token,
                expires_at=issued.expires_at,
            )
        return ConfirmPauseFocusAction(
            confirmation_token=issued.token,
            expires_at=issued.expires_at,
        )

    def resolve(
        self,
        db: Session,
        *,
        user_id: str,
        token: str,
        decision: str,
    ) -> ResolveAgentActionResponse:
        action_type, arguments = AgentActionRepository(db).resolve(
            user_id=user_id,
            token=token,
            decision=decision,
        )
        if decision == "reject":
            return ResolveAgentActionResponse(
                accepted=False,
                action=None,
                message="已取消这个操作",
            )
        if action_type == "start_focus":
            duration = arguments.get("durationMinutes")
            if (
                set(arguments) != {"durationMinutes"}
                or not isinstance(duration, int)
                or isinstance(duration, bool)
                or not 5 <= duration <= 120
            ):
                raise ActionResolutionError(
                    "ACTION_TAMPERED", "确认参数校验失败"
                )
            return ResolveAgentActionResponse(
                accepted=True,
                action=StartFocusAction(
                    duration_minutes=duration
                ),
                message="已确认开始专注",
            )
        if action_type == "pause_focus" and arguments == {}:
            return ResolveAgentActionResponse(
                accepted=True,
                action=PauseFocusAction(),
                message="已确认暂停专注",
            )
        raise ActionResolutionError("ACTION_TAMPERED", "确认动作校验失败")
