"""受控长期记忆的数据访问。"""

from datetime import datetime

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..db.models import UserMemory


class MemoryRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_owned(self, user_id: str) -> list[UserMemory]:
        return list(
            self.db.scalars(
                select(UserMemory)
                .where(UserMemory.user_id == user_id)
                .order_by(UserMemory.category.asc())
            )
        )

    def get(self, user_id: str, category: str) -> UserMemory | None:
        return self.db.scalar(
            select(UserMemory).where(
                UserMemory.user_id == user_id, UserMemory.category == category
            )
        )

    def upsert(
        self,
        user_id: str,
        category: str,
        content: str,
        *,
        source: str,
        now: datetime,
    ) -> UserMemory:
        item = self.get(user_id, category)
        if item is None:
            item = UserMemory(
                user_id=user_id,
                category=category,
                content=content,
                source=source,
                created_at=now,
                updated_at=now,
            )
            self.db.add(item)
        else:
            item.content = content
            item.source = source
            item.updated_at = now
        self.db.flush()
        return item

    def delete(self, user_id: str, category: str) -> None:
        self.db.execute(
            delete(UserMemory).where(
                UserMemory.user_id == user_id, UserMemory.category == category
            )
        )

