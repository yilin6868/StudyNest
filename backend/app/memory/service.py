"""用户可查看、修改和删除的受控长期记忆。"""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from ..repositories.memories import MemoryRepository
from .contracts import MemoryItem, MemoryList
from .policy import validate_memory


class MemoryService:
    def list(self, db: Session, user_id: str) -> MemoryList:
        values = MemoryRepository(db).list_owned(user_id)
        return MemoryList(
            memories=[
                MemoryItem(
                    category=item.category,
                    content=item.content,
                    updated_at=item.updated_at,
                )
                for item in values
            ]
        )

    def save(
        self,
        db: Session,
        user_id: str,
        category: str,
        content: str,
        *,
        source: str,
    ) -> MemoryItem:
        clean = validate_memory(category, content)
        item = MemoryRepository(db).upsert(
            user_id,
            category,
            clean,
            source=source,
            now=datetime.now(timezone.utc),
        )
        return MemoryItem(
            category=item.category, content=item.content, updated_at=item.updated_at
        )

    def delete(self, db: Session, user_id: str, category: str) -> None:
        validate_memory(category, "x")
        MemoryRepository(db).delete(user_id, category)

