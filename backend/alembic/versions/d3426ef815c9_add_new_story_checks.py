"""add new story checks

Revision ID: d3426ef815c9
Revises: c21db3097ef4
"""
from alembic import op
import sqlalchemy as sa


revision = "d3426ef815c9"
down_revision = "c21db3097ef4"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "new_story_checks",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("input_json", sa.Text(), nullable=False),
        sa.Column("result_json", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="checked"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_new_story_checks_session_id", "new_story_checks", ["session_id"])
    op.create_index("ix_new_story_checks_status", "new_story_checks", ["status"])


def downgrade() -> None:
    op.drop_index("ix_new_story_checks_status", table_name="new_story_checks")
    op.drop_index("ix_new_story_checks_session_id", table_name="new_story_checks")
    op.drop_table("new_story_checks")
