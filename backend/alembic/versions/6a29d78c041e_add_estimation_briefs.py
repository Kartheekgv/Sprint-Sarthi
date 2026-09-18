"""add estimation briefs

Revision ID: 6a29d78c041e
Revises: 3d61d2a85f6b
"""
from alembic import op
import sqlalchemy as sa


revision = "6a29d78c041e"
down_revision = "3d61d2a85f6b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "estimation_briefs",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("answered_by", sa.String(length=200), nullable=False),
        sa.Column("answers_json", sa.Text(), nullable=False),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_estimation_briefs_session_id", "estimation_briefs", ["session_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_estimation_briefs_session_id", table_name="estimation_briefs")
    op.drop_table("estimation_briefs")