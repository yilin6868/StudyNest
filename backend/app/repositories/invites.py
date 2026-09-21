"""邀请码数据访问与原子名额占用。"""

from datetime import datetime

from sqlalchemy import and_, or_, select, update
from sqlalchemy.orm import Session

from ..db.models import InviteCode, InviteRedemption


class InviteRepository:
    def __init__(self, db: Session):
        self.db = db

    def get_by_digest(self, digest: str) -> InviteCode | None:
        return self.db.scalar(select(InviteCode).where(InviteCode.code_digest == digest))

    def create(
        self,
        *,
        invite_id: str,
        digest: str,
        max_uses: int | None,
        expires_at: datetime | None,
        now: datetime,
    ) -> InviteCode:
        invite = InviteCode(
            id=invite_id,
            code_digest=digest,
            max_uses=max_uses,
            used_count=0,
            expires_at=expires_at,
            disabled_at=None,
            created_at=now,
        )
        self.db.add(invite)
        return invite

    def consume(self, invite_id: str, *, now: datetime) -> bool:
        result = self.db.execute(
            update(InviteCode)
            .where(
                InviteCode.id == invite_id,
                InviteCode.disabled_at.is_(None),
                or_(InviteCode.expires_at.is_(None), InviteCode.expires_at > now),
                or_(
                    InviteCode.max_uses.is_(None),
                    and_(
                        InviteCode.max_uses.is_not(None),
                        InviteCode.used_count < InviteCode.max_uses,
                    ),
                ),
            )
            .values(used_count=InviteCode.used_count + 1)
            .execution_options(synchronize_session=False)
        )
        return result.rowcount == 1

    def add_redemption(
        self, *, redemption_id: str, invite_id: str, user_id: str, now: datetime
    ) -> None:
        self.db.add(
            InviteRedemption(
                id=redemption_id,
                invite_code_id=invite_id,
                user_id=user_id,
                created_at=now,
            )
        )

    def disable(self, invite_id: str, *, now: datetime) -> bool:
        result = self.db.execute(
            update(InviteCode)
            .where(InviteCode.id == invite_id, InviteCode.disabled_at.is_(None))
            .values(disabled_at=now)
        )
        return result.rowcount == 1
