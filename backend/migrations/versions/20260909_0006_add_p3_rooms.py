"""P3-G minimal study rooms."""
from alembic import op
import sqlalchemy as sa
revision = "20260909_0006"
down_revision = "20260909_0005"
branch_labels = None
depends_on = None
def upgrade() -> None:
    op.create_table("study_rooms", sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("owner_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("invite_token_digest", sa.String(64), unique=True, nullable=False), sa.Column("status", sa.String(16), nullable=False, server_default="active"), sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False))
    op.create_table("study_room_members", sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("room_id", sa.String(36), sa.ForeignKey("study_rooms.id", ondelete="CASCADE"), nullable=False), sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("status", sa.String(16), nullable=False, server_default="active"), sa.Column("focus_status", sa.String(16), nullable=False, server_default="idle"), sa.Column("last_seen_at", sa.DateTime(timezone=True), nullable=False), sa.UniqueConstraint("room_id", "user_id", name="uq_study_room_member"))
    op.create_table("study_room_reports", sa.Column("id", sa.String(36), primary_key=True), sa.Column("created_at", sa.DateTime(timezone=True), nullable=False), sa.Column("room_id", sa.String(36), sa.ForeignKey("study_rooms.id", ondelete="CASCADE"), nullable=False), sa.Column("reporter_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False), sa.Column("reason", sa.String(255), nullable=False))
def downgrade() -> None:
    op.drop_table("study_room_reports"); op.drop_table("study_room_members"); op.drop_table("study_rooms")
