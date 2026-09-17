"""add sprint plan decisions

Revision ID: 0a3eaf752c38
Revises: f82d9e641b27
"""
from alembic import op
import sqlalchemy as sa


revision = "0a3eaf752c38"
down_revision = "f82d9e641b27"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "sprint_plan_decisions",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("story_id", sa.String(length=36), nullable=False),
        sa.Column("sprint_id", sa.String(length=36), nullable=True),
        sa.Column("assignee_id", sa.String(length=36), nullable=True),
        sa.Column("decision", sa.String(length=20), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("decision IN ('planned', 'deferred')", name="ck_sprint_plan_decision"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_sprint_plan_confidence"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["story_id"], ["user_stories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["sprint_id"], ["sprints.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["assignee_id"], ["team_members.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "story_id", name="uq_session_sprint_plan_story"),
    )
    for column in ("project_id", "session_id", "story_id", "sprint_id", "assignee_id", "decision", "status"):
        op.create_index(f"ix_sprint_plan_decisions_{column}", "sprint_plan_decisions", [column])


def downgrade() -> None:
    op.drop_table("sprint_plan_decisions")