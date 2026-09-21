"""增加 P1-C 会话记忆、受控长期记忆和脱敏 Agent 轨迹。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_0003"
down_revision: str | Sequence[str] | None = "20260909_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("chat_sessions") as batch:
        batch.add_column(sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("summary", sa.Text(), nullable=True))
        batch.add_column(
            sa.Column("summary_message_count", sa.Integer(), nullable=False, server_default="0")
        )
        batch.add_column(sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(
            sa.Column("status", sa.String(16), nullable=False, server_default="active")
        )
        batch.create_check_constraint(
            "ck_chat_sessions_status", "status IN ('active', 'archived')"
        )
        batch.create_check_constraint(
            "ck_chat_summary_message_count_non_negative", "summary_message_count >= 0"
        )
        batch.create_index(
            "ix_chat_sessions_user_updated", ["user_id", "updated_at"], unique=False
        )
    op.execute("UPDATE chat_sessions SET updated_at = created_at WHERE updated_at IS NULL")
    with op.batch_alter_table("chat_sessions") as batch:
        batch.alter_column("updated_at", nullable=False)

    with op.batch_alter_table("chat_messages") as batch:
        batch.create_check_constraint(
            "ck_chat_messages_role", "role IN ('user', 'assistant', 'safety_marker')"
        )
        batch.create_index(
            "ix_chat_messages_session_created",
            ["chat_session_id", "created_at"],
            unique=False,
        )

    op.create_table(
        "user_memories",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("category", sa.String(32), nullable=False),
        sa.Column("content", sa.String(120), nullable=False),
        sa.Column("source", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "category IN ('study_routine', 'learning_preference', 'companionship_style')",
            name="ck_user_memories_category",
        ),
        sa.CheckConstraint(
            "source IN ('user_ui', 'explicit_chat')", name="ck_user_memories_source"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "category", name="uq_user_memory_category"),
    )

    with op.batch_alter_table("agent_events") as batch:
        batch.add_column(
            sa.Column("sequence", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(
            sa.Column("outcome", sa.String(16), nullable=False, server_default="started")
        )
        batch.add_column(sa.Column("duration_ms", sa.Integer(), nullable=True))
        batch.add_column(
            sa.Column("schema_version", sa.Integer(), nullable=False, server_default="1")
        )
        batch.create_check_constraint(
            "ck_agent_events_outcome",
            "outcome IN ('started', 'succeeded', 'failed', 'blocked', 'fallback')",
        )
        batch.create_check_constraint("ck_agent_events_sequence_positive", "sequence > 0")
        batch.create_check_constraint(
            "ck_agent_events_duration_non_negative",
            "duration_ms IS NULL OR duration_ms >= 0",
        )
        batch.create_index(
            "ix_agent_events_request_sequence", ["request_id", "sequence"], unique=False
        )
        batch.create_index(
            "ix_agent_events_user_created", ["user_id", "created_at"], unique=False
        )
        batch.create_index(
            "ix_agent_events_type_created", ["event_type", "created_at"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("agent_events") as batch:
        batch.drop_index("ix_agent_events_type_created")
        batch.drop_index("ix_agent_events_user_created")
        batch.drop_index("ix_agent_events_request_sequence")
        batch.drop_constraint("ck_agent_events_duration_non_negative", type_="check")
        batch.drop_constraint("ck_agent_events_sequence_positive", type_="check")
        batch.drop_constraint("ck_agent_events_outcome", type_="check")
        batch.drop_column("schema_version")
        batch.drop_column("duration_ms")
        batch.drop_column("outcome")
        batch.drop_column("sequence")

    op.drop_table("user_memories")

    with op.batch_alter_table("chat_messages") as batch:
        batch.drop_index("ix_chat_messages_session_created")
        batch.drop_constraint("ck_chat_messages_role", type_="check")

    with op.batch_alter_table("chat_sessions") as batch:
        batch.drop_index("ix_chat_sessions_user_updated")
        batch.drop_constraint("ck_chat_summary_message_count_non_negative", type_="check")
        batch.drop_constraint("ck_chat_sessions_status", type_="check")
        batch.drop_column("status")
        batch.drop_column("summary_updated_at")
        batch.drop_column("summary_message_count")
        batch.drop_column("summary")
        batch.drop_column("updated_at")
