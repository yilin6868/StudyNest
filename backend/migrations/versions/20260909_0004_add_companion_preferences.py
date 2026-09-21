"""增加 P2 主动陪伴偏好字段。"""
from collections.abc import Sequence
import sqlalchemy as sa
from alembic import op

revision: str = "20260909_0004"
down_revision: str | Sequence[str] | None = "20260909_0003"
branch_labels = None
depends_on = None

def upgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch:
        batch.add_column(sa.Column("mid_session_encouragement_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("proactive_reminder_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch.add_column(sa.Column("quiet_hours_start", sa.String(5), nullable=True))
        batch.add_column(sa.Column("quiet_hours_end", sa.String(5), nullable=True))

def downgrade() -> None:
    with op.batch_alter_table("user_preferences") as batch:
        batch.drop_column("quiet_hours_end")
        batch.drop_column("quiet_hours_start")
        batch.drop_column("proactive_reminder_enabled")
        batch.drop_column("mid_session_encouragement_enabled")
