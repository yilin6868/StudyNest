"""用户会话与消息的数据访问；所有查询都绑定数据所有者。"""

from datetime import datetime

from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from ..db.models import ChatMessage, ChatSession


class ConversationRepository:
    def __init__(self, db: Session):
        self.db = db

    def create(self, user_id: str, *, now: datetime) -> ChatSession:
        item = ChatSession(
            user_id=user_id,
            title=None,
            summary=None,
            summary_message_count=0,
            summary_updated_at=None,
            status="active",
            created_at=now,
            updated_at=now,
        )
        self.db.add(item)
        self.db.flush()
        return item

    def get_owned(self, user_id: str, session_id: str) -> ChatSession | None:
        return self.db.scalar(
            select(ChatSession).where(
                ChatSession.id == session_id, ChatSession.user_id == user_id
            )
        )

    def list_owned(self, user_id: str, *, limit: int = 20) -> list[ChatSession]:
        return list(
            self.db.scalars(
                select(ChatSession)
                .where(ChatSession.user_id == user_id)
                .order_by(ChatSession.updated_at.desc(), ChatSession.id.desc())
                .limit(limit)
            )
        )

    def add_message(
        self,
        session: ChatSession,
        *,
        role: str,
        content: str,
        now: datetime,
    ) -> ChatMessage:
        message = ChatMessage(
            chat_session_id=session.id,
            role=role,
            content=content,
            created_at=now,
        )
        self.db.add(message)
        session.updated_at = now
        if session.title is None and role == "user":
            session.title = content[:40]
        self.db.flush()
        return message

    def recent_messages(self, session_id: str, *, limit: int) -> list[ChatMessage]:
        values = list(
            self.db.scalars(
                select(ChatMessage)
                .where(ChatMessage.chat_session_id == session_id)
                .order_by(ChatMessage.created_at.desc(), ChatMessage.id.desc())
                .limit(limit)
            )
        )
        return list(reversed(values))

    def messages_after_summary(
        self, session: ChatSession, *, exclude_recent: int
    ) -> list[ChatMessage]:
        values = list(
            self.db.scalars(
                select(ChatMessage)
                .where(ChatMessage.chat_session_id == session.id)
                .order_by(ChatMessage.created_at.asc(), ChatMessage.id.asc())
            )
        )
        start = min(session.summary_message_count, len(values))
        end = max(start, len(values) - exclude_recent)
        return values[start:end]

    def count_messages(self, session_id: str) -> int:
        return int(
            self.db.scalar(
                select(func.count())
                .select_from(ChatMessage)
                .where(ChatMessage.chat_session_id == session_id)
            )
            or 0
        )

    def delete_owned(self, user_id: str, session_id: str) -> bool:
        session = self.get_owned(user_id, session_id)
        if session is None:
            return False
        # SQLite 开发环境也明确删除子记录，不依赖连接级 PRAGMA。
        self.db.execute(
            delete(ChatMessage).where(ChatMessage.chat_session_id == session.id)
        )
        self.db.delete(session)
        return True

