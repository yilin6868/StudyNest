"""一次性 Agent 前端动作确认记录。"""

from __future__ import annotations

import hashlib
import json
import secrets
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..agent.context import canonical_arguments, digest_arguments
from ..db.models import AgentActionConfirmation


def _token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _aware(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=timezone.utc)


@dataclass(frozen=True)
class IssuedAction:
    token: str
    expires_at: datetime
    action_type: str
    arguments: dict


class ActionResolutionError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 409) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class AgentActionRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def issue(
        self,
        *,
        user_id: str,
        request_id: str,
        action_type: str,
        arguments: dict,
        ttl_seconds: int,
        now: datetime | None = None,
    ) -> IssuedAction:
        now = now or datetime.now(timezone.utc)
        token = secrets.token_urlsafe(32)
        expires_at = now + timedelta(seconds=ttl_seconds)
        self.db.add(
            AgentActionConfirmation(
                user_id=user_id,
                request_id=request_id,
                token_digest=_token_digest(token),
                action_type=action_type,
                arguments_json=canonical_arguments(arguments),
                arguments_digest=digest_arguments(arguments),
                status="pending",
                expires_at=expires_at,
                created_at=now,
            )
        )
        self.db.flush()
        return IssuedAction(token, expires_at, action_type, arguments)

    def resolve(
        self,
        *,
        user_id: str,
        token: str,
        decision: str,
        now: datetime | None = None,
    ) -> tuple[str, dict]:
        now = now or datetime.now(timezone.utc)
        digest = _token_digest(token)
        record = self.db.scalar(
            select(AgentActionConfirmation).where(
                AgentActionConfirmation.token_digest == digest,
                AgentActionConfirmation.user_id == user_id,
            )
        )
        if record is None:
            raise ActionResolutionError("ACTION_NOT_FOUND", "确认操作不存在", 404)
        if record.status != "pending":
            raise ActionResolutionError("ACTION_ALREADY_RESOLVED", "这个操作已经处理过了")
        if _aware(record.expires_at) <= _aware(now):
            self.db.execute(
                update(AgentActionConfirmation)
                .where(
                    AgentActionConfirmation.id == record.id,
                    AgentActionConfirmation.status == "pending",
                )
                .values(status="expired", resolved_at=now)
            )
            self.db.commit()
            raise ActionResolutionError("ACTION_EXPIRED", "这个确认已经过期了")

        new_status = "confirmed" if decision == "confirm" else "rejected"
        changed = self.db.execute(
            update(AgentActionConfirmation)
            .where(
                AgentActionConfirmation.id == record.id,
                AgentActionConfirmation.status == "pending",
            )
            .values(status=new_status, resolved_at=now)
        ).rowcount
        if changed != 1:
            self.db.rollback()
            raise ActionResolutionError("ACTION_ALREADY_RESOLVED", "这个操作已经处理过了")

        arguments = json.loads(record.arguments_json)
        if record.arguments_digest != digest_arguments(arguments):
            self.db.rollback()
            raise ActionResolutionError("ACTION_TAMPERED", "确认参数校验失败")
        self.db.commit()
        return record.action_type, arguments
