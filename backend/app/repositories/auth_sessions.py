"""登录会话数据访问。"""

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from ..db.models import AuthSession, User


class AuthSessionRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(
        self,
        *,
        session_id: str,
        user_id: str,
        token_hash: str,
        expires_at: datetime,
        now: datetime,
    ) -> AuthSession:
        auth_session = AuthSession(
            id=session_id,
            user_id=user_id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked_at=None,
            last_seen_at=None,
            created_at=now,
        )
        self.db.add(auth_session)
        return auth_session

    def active_user(self, token_hash: str, *, now: datetime) -> User | None:
        return self.db.scalar(
            select(User)
            .join(AuthSession, AuthSession.user_id == User.id)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
                AuthSession.expires_at > now,
                User.status == "active",
            )
        )

    def revoke(self, token_hash: str, *, now: datetime) -> bool:
        result = self.db.execute(
            update(AuthSession)
            .where(
                AuthSession.token_hash == token_hash,
                AuthSession.revoked_at.is_(None),
            )
            .values(revoked_at=now)
        )
        return result.rowcount == 1

    def revoke_all(self, user_id: str, *, now: datetime) -> int:
        result = self.db.execute(
            update(AuthSession)
            .where(AuthSession.user_id == user_id, AuthSession.revoked_at.is_(None))
            .values(revoked_at=now)
        )
        return result.rowcount
