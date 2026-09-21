"""P0-C 数据模型：账号、会话、学习事实和迁移记录。"""

from datetime import date, datetime
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base


def new_id() -> str:
    return str(uuid4())


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    username_normalized: Mapped[str | None] = mapped_column(
        String(64), unique=True, nullable=True
    )
    password_hash: Mapped[str | None] = mapped_column(String(512), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Shanghai")
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="active")
    legacy_user_key: Mapped[str | None] = mapped_column(
        String(128), unique=True, nullable=True
    )
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'legacy_unclaimed', 'disabled')",
            name="ck_users_status",
        ),
    )


class InviteCode(TimestampMixin, Base):
    __tablename__ = "invite_codes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    max_uses: Mapped[int | None] = mapped_column(Integer, nullable=True)
    used_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        CheckConstraint("used_count >= 0", name="ck_invite_used_count_non_negative"),
        CheckConstraint(
            "max_uses IS NULL OR max_uses > 0",
            name="ck_invite_max_uses_positive",
        ),
    )


class InviteRedemption(TimestampMixin, Base):
    __tablename__ = "invite_redemptions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    invite_code_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("invite_codes.id", ondelete="RESTRICT"), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )


class AuthSession(TimestampMixin, Base):
    __tablename__ = "auth_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_auth_sessions_user_active", "user_id", "revoked_at", "expires_at"),
    )


class StudySession(TimestampMixin, Base):
    __tablename__ = "study_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    client_session_id: Mapped[str] = mapped_column(String(36), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="completed")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="app")

    __table_args__ = (
        UniqueConstraint("user_id", "client_session_id", name="uq_study_user_session"),
        CheckConstraint("minutes >= 0", name="ck_study_minutes_non_negative"),
        Index("ix_study_user_completed", "user_id", "completed_at"),
    )


class DailyStudyRecord(Base):
    __tablename__ = "daily_study_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    study_date: Mapped[date] = mapped_column(Date, nullable=False)
    tomato_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "study_date", name="uq_daily_user_date"),
        CheckConstraint("tomato_count >= 0", name="ck_daily_tomato_non_negative"),
        CheckConstraint("minutes >= 0", name="ck_daily_minutes_non_negative"),
    )


class DailyGoal(TimestampMixin, Base):
    __tablename__ = "daily_goals"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    goal_date: Mapped[date] = mapped_column(Date, nullable=False)
    text: Mapped[str] = mapped_column(String(60), nullable=False, default="")
    source: Mapped[str] = mapped_column(String(32), nullable=False, default="app")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "goal_date", name="uq_goal_user_date"),
    )


class ChatSession(TimestampMixin, Base):
    __tablename__ = "chat_sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    title: Mapped[str | None] = mapped_column(String(120), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    summary_message_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    summary_updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")

    __table_args__ = (
        CheckConstraint(
            "status IN ('active', 'archived')", name="ck_chat_sessions_status"
        ),
        CheckConstraint(
            "summary_message_count >= 0",
            name="ck_chat_summary_message_count_non_negative",
        ),
        Index("ix_chat_sessions_user_updated", "user_id", "updated_at"),
    )


class ChatMessage(TimestampMixin, Base):
    __tablename__ = "chat_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    chat_session_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False
    )
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    __table_args__ = (
        CheckConstraint(
            "role IN ('user', 'assistant', 'safety_marker')",
            name="ck_chat_messages_role",
        ),
        Index(
            "ix_chat_messages_session_created", "chat_session_id", "created_at"
        ),
    )


class UserMemory(TimestampMixin, Base):
    __tablename__ = "user_memories"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    category: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(String(120), nullable=False)
    source: Mapped[str] = mapped_column(String(24), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        UniqueConstraint("user_id", "category", name="uq_user_memory_category"),
        CheckConstraint(
            "category IN ('study_routine', 'learning_preference', 'companionship_style')",
            name="ck_user_memories_category",
        ),
        CheckConstraint(
            "source IN ('user_ui', 'explicit_chat')",
            name="ck_user_memories_source",
        ),
    )


class UserPreference(TimestampMixin, Base):
    __tablename__ = "user_preferences"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    buddy_gender: Mapped[str] = mapped_column(String(16), nullable=False, default="female")
    voice_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    mid_session_encouragement_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    proactive_reminder_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    quiet_hours_start: Mapped[str | None] = mapped_column(String(5), nullable=True)
    quiet_hours_end: Mapped[str | None] = mapped_column(String(5), nullable=True)
    custom_focus_enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    default_focus_minutes: Mapped[int] = mapped_column(Integer, nullable=False, default=25)
    reminder_channel: Mapped[str] = mapped_column(String(16), nullable=False, default="in_app")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class AchievementDefinition(TimestampMixin, Base):
    __tablename__ = "achievement_definitions"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(120), nullable=False)
    description: Mapped[str] = mapped_column(String(255), nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class UserAchievement(TimestampMixin, Base):
    __tablename__ = "user_achievements"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    achievement_code: Mapped[str] = mapped_column(String(64), nullable=False)
    rule_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    awarded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    hidden_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    __table_args__ = (UniqueConstraint("user_id", "achievement_code", "rule_version", name="uq_user_achievement_rule"),)


class StudyRoom(TimestampMixin, Base):
    __tablename__ = "study_rooms"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    owner_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    invite_token_digest: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (CheckConstraint("status IN ('active', 'closed')", name="ck_study_room_status"),)


class StudyRoomMember(TimestampMixin, Base):
    __tablename__ = "study_room_members"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("study_rooms.id", ondelete="CASCADE"), nullable=False)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="active")
    focus_status: Mapped[str] = mapped_column(String(16), nullable=False, default="idle")
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    __table_args__ = (UniqueConstraint("room_id", "user_id", name="uq_study_room_member"),)


class StudyRoomReport(TimestampMixin, Base):
    __tablename__ = "study_room_reports"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    room_id: Mapped[str] = mapped_column(String(36), ForeignKey("study_rooms.id", ondelete="CASCADE"), nullable=False)
    reporter_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(String(255), nullable=False)


class AgentEvent(TimestampMixin, Base):
    __tablename__ = "agent_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    payload: Mapped[str | None] = mapped_column(Text, nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    outcome: Mapped[str] = mapped_column(String(16), nullable=False, default="started")
    duration_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    schema_version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        CheckConstraint(
            "outcome IN ('started', 'succeeded', 'failed', 'blocked', 'fallback')",
            name="ck_agent_events_outcome",
        ),
        CheckConstraint("sequence > 0", name="ck_agent_events_sequence_positive"),
        CheckConstraint(
            "duration_ms IS NULL OR duration_ms >= 0",
            name="ck_agent_events_duration_non_negative",
        ),
        Index("ix_agent_events_request_sequence", "request_id", "sequence"),
        Index("ix_agent_events_user_created", "user_id", "created_at"),
        Index("ix_agent_events_type_created", "event_type", "created_at"),
    )


class AgentActionConfirmation(TimestampMixin, Base):
    __tablename__ = "agent_action_confirmations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    request_id: Mapped[str] = mapped_column(String(64), nullable=False)
    token_digest: Mapped[str] = mapped_column(String(64), nullable=False, unique=True)
    action_type: Mapped[str] = mapped_column(String(32), nullable=False)
    arguments_json: Mapped[str] = mapped_column(Text, nullable=False)
    arguments_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        CheckConstraint(
            "action_type IN ('start_focus', 'pause_focus')",
            name="ck_agent_action_type",
        ),
        CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected', 'expired')",
            name="ck_agent_action_status",
        ),
        Index(
            "ix_agent_action_user_status_expires",
            "user_id",
            "status",
            "expires_at",
        ),
    )


class MigrationRun(TimestampMixin, Base):
    __tablename__ = "migration_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    source_key_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    source_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False, default="{}")
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint(
            "source_key_hash", "source_checksum", name="uq_migration_source_checksum"
        ),
    )
