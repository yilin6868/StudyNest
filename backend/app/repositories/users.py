"""用户数据访问。"""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db.models import User


class UserRepository:
    def __init__(self, db: Session):
        self.db = db

    def get(self, user_id: str) -> User | None:
        return self.db.get(User, user_id)

    def get_by_username(self, normalized: str) -> User | None:
        return self.db.scalar(
            select(User).where(User.username_normalized == normalized)
        )

    def get_by_legacy_key(self, legacy_user_key: str) -> User | None:
        return self.db.scalar(
            select(User).where(User.legacy_user_key == legacy_user_key)
        )

    def create(
        self,
        *,
        user_id: str,
        username: str | None,
        username_normalized: str | None,
        password_hash: str | None,
        timezone_name: str,
        status: str,
        now: datetime,
        legacy_user_key: str | None = None,
    ) -> User:
        user = User(
            id=user_id,
            username=username,
            username_normalized=username_normalized,
            password_hash=password_hash,
            timezone=timezone_name,
            status=status,
            legacy_user_key=legacy_user_key,
            created_at=now,
            updated_at=now,
        )
        self.db.add(user)
        return user
