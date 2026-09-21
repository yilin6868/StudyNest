"""P3 foundations: custom focus and achievements."""
from alembic import op
import sqlalchemy as sa

revision = "20260909_0005"
down_revision = "20260909_0004"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("user_preferences", sa.Column("custom_focus_enabled", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user_preferences", sa.Column("default_focus_minutes", sa.Integer(), nullable=False, server_default="25"))
    op.add_column("user_preferences", sa.Column("reminder_channel", sa.String(length=16), nullable=False, server_default="in_app"))
    op.create_table("achievement_definitions",
        sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True), sa.Column("title", sa.String(length=120), nullable=False),
        sa.Column("description", sa.String(length=255), nullable=False), sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"), sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_table("user_achievements",
        sa.Column("id", sa.String(length=36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("user_id", sa.String(length=36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("achievement_code", sa.String(length=64), nullable=False),
        sa.Column("rule_version", sa.Integer(), nullable=False, server_default="1"), sa.Column("awarded_at", sa.DateTime(timezone=True), nullable=False), sa.Column("hidden_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("user_id", "achievement_code", "rule_version", name="uq_user_achievement_rule"))

def downgrade() -> None:
    op.drop_table("user_achievements"); op.drop_table("achievement_definitions")
    op.drop_column("user_preferences", "reminder_channel"); op.drop_column("user_preferences", "default_focus_minutes"); op.drop_column("user_preferences", "custom_focus_enabled")
