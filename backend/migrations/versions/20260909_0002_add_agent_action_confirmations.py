"""增加 P1-B 一次性 Agent 动作确认记录。"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260909_0002"
down_revision: str | Sequence[str] | None = "20260909_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "agent_action_confirmations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("request_id", sa.String(64), nullable=False),
        sa.Column("token_digest", sa.String(64), nullable=False, unique=True),
        sa.Column("action_type", sa.String(32), nullable=False),
        sa.Column("arguments_json", sa.Text(), nullable=False),
        sa.Column("arguments_digest", sa.String(64), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "action_type IN ('start_focus', 'pause_focus')",
            name="ck_agent_action_type",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'confirmed', 'rejected', 'expired')",
            name="ck_agent_action_status",
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        "ix_agent_action_user_status_expires",
        "agent_action_confirmations",
        ["user_id", "status", "expires_at"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_agent_action_user_status_expires",
        table_name="agent_action_confirmations",
    )
    op.drop_table("agent_action_confirmations")
