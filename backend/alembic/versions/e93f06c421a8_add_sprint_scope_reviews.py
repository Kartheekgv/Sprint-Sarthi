"""add sprint scope reviews

Revision ID: e93f06c421a8
Revises: d3426ef815c9
"""
from alembic import op
import sqlalchemy as sa


revision = "e93f06c421a8"
down_revision = "d3426ef815c9"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sprint_scope_reviews",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("reviewed_by", sa.String(length=200), nullable=False),
        sa.Column("selected_task_ids_json", sa.Text(), nullable=False),
        sa.Column("discarded_task_ids_json", sa.Text(), nullable=False),
        sa.Column("selected_story_ids_json", sa.Text(), nullable=False),
        sa.Column("note", sa.Text(), nullable=False, server_default=""),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_sprint_scope_reviews_project_id", "sprint_scope_reviews", ["project_id"])
    op.create_index("ix_sprint_scope_reviews_session_id", "sprint_scope_reviews", ["session_id"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_sprint_scope_reviews_session_id", table_name="sprint_scope_reviews")
    op.drop_index("ix_sprint_scope_reviews_project_id", table_name="sprint_scope_reviews")
    op.drop_table("sprint_scope_reviews")