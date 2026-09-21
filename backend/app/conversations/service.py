"""有界会话生命周期、恢复和摘要状态。"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from ..agent.contracts import ConversationMessage, LearningMemory
from ..core.config import settings
from ..db.models import ChatSession
from ..repositories.conversations import ConversationRepository
from ..repositories.memories import MemoryRepository
from ..safety.responses import SAFETY_RESPONSE_MARKER
from .context import ConversationContext, fit_context
from .contracts import (
    ConversationCreateResponse,
    ConversationItem,
    ConversationList,
    ConversationMessageItem,
    ConversationMessages,
)


class ConversationNotFoundError(LookupError):
    pass


class ConversationService:
    def resolve(
        self, db: Session, user_id: str, session_id: str | None
    ) -> tuple[ChatSession, bool]:
        repository = ConversationRepository(db)
        if session_id is not None:
            value = repository.get_owned(user_id, session_id)
            if value is None:
                raise ConversationNotFoundError
            return value, False
        value = repository.create(user_id, now=datetime.now(timezone.utc))
        db.commit()
        return value, True

    def create(self, db: Session, user_id: str) -> ConversationCreateResponse:
        value = ConversationRepository(db).create(
            user_id, now=datetime.now(timezone.utc)
        )
        db.commit()
        return ConversationCreateResponse(session_id=value.id)

    def list(self, db: Session, user_id: str) -> ConversationList:
        values = ConversationRepository(db).list_owned(
            user_id, limit=settings.chat_session_list_limit
        )
        return ConversationList(
            sessions=[
                ConversationItem(
                    session_id=item.id,
                    title=item.title,
                    status=item.status,
                    updated_at=item.updated_at,
                )
                for item in values
            ]
        )

    def messages(
        self, db: Session, user_id: str, session_id: str
    ) -> ConversationMessages:
        repository = ConversationRepository(db)
        if repository.get_owned(user_id, session_id) is None:
            raise ConversationNotFoundError
        values = repository.recent_messages(
            session_id, limit=settings.chat_page_message_limit
        )
        return ConversationMessages(
            session_id=session_id,
            messages=[
                ConversationMessageItem(
                    role=item.role, content=item.content, created_at=item.created_at
                )
                for item in values
            ],
        )

    def delete(self, db: Session, user_id: str, session_id: str) -> None:
        if not ConversationRepository(db).delete_owned(user_id, session_id):
            raise ConversationNotFoundError
        db.commit()

    def context(
        self, db: Session, user_id: str, session: ChatSession
    ) -> ConversationContext:
        repository = ConversationRepository(db)
        messages = [
            ConversationMessage(role=item.role, content=item.content)
            for item in repository.recent_messages(
                session.id, limit=settings.chat_recent_message_limit
            )
            if item.role in {"user", "assistant"}
        ]
        memories = [
            LearningMemory(category=item.category, content=item.content)
            for item in MemoryRepository(db).list_owned(user_id)
        ]
        return fit_context(
            summary=session.summary or "",
            recent_messages=messages,
            memories=memories,
            max_bytes=settings.agent_context_max_bytes // 2,
        )

    def save_exchange(
        self,
        db: Session,
        session: ChatSession,
        *,
        user_text: str,
        assistant_text: str,
        safety_marker: bool = False,
        response_safety: bool = False,
    ) -> None:
        repository = ConversationRepository(db)
        now = datetime.now(timezone.utc)
        repository.add_message(
            session,
            role="safety_marker" if safety_marker else "user",
            content=user_text,
            now=now,
        )
        if response_safety and not safety_marker:
            repository.add_message(
                session,
                role="safety_marker",
                content=SAFETY_RESPONSE_MARKER,
                now=now + timedelta(microseconds=1),
            )
        repository.add_message(
            session,
            role="assistant",
            content=assistant_text,
            now=now + timedelta(microseconds=2),
        )
        db.commit()

    def summary_candidates(
        self, db: Session, session: ChatSession
    ) -> tuple[list, int]:
        repository = ConversationRepository(db)
        count = repository.count_messages(session.id)
        candidates = repository.messages_after_summary(
            session, exclude_recent=settings.chat_recent_message_limit
        )
        chars = sum(len(item.content) for item in candidates)
        uncovered = count - session.summary_message_count
        if uncovered <= settings.chat_summary_trigger_count and chars <= settings.chat_summary_trigger_chars:
            return [], count
        return candidates, count

    def update_summary(
        self, db: Session, session: ChatSession, summary: str, covered_count: int
    ) -> None:
        session.summary = summary[: settings.chat_summary_max_chars]
        session.summary_message_count = max(
            session.summary_message_count,
            max(0, covered_count - settings.chat_recent_message_limit),
        )
        session.summary_updated_at = datetime.now(timezone.utc)
        db.commit()
