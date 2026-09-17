"""add leave and assignments

Revision ID: f82d9e641b27
Revises: e71c8d530a16
"""
from alembic import op
import sqlalchemy as sa


revision = "f82d9e641b27"
down_revision = "e71c8d530a16"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "leaves",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("team_member_id", sa.String(length=36), nullable=False),
        sa.Column("start_date", sa.Date(), nullable=False),
        sa.Column("end_date", sa.Date(), nullable=False),
        sa.Column("reason", sa.String(length=300), nullable=False, server_default=""),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("end_date >= start_date", name="ck_leave_dates"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_member_id"], ["team_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_leaves_project_id", "leaves", ["project_id"])
    op.create_index("ix_leaves_team_member_id", "leaves", ["team_member_id"])
    op.create_table(
        "assignment_recommendations",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("item_stable_id", sa.String(length=50), nullable=False),
        sa.Column("team_member_id", sa.String(length=36), nullable=False),
        sa.Column("recommended_hours", sa.Float(), nullable=True),
        sa.Column("match_score", sa.Float(), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="proposed"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("match_score BETWEEN 0 AND 1", name="ck_assignment_match_score"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_assignment_confidence"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["team_member_id"], ["team_members.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "item_stable_id", name="uq_session_assignment_item"),
    )
    op.create_index("ix_assignment_recommendations_project_id", "assignment_recommendations", ["project_id"])
    op.create_index("ix_assignment_recommendations_session_id", "assignment_recommendations", ["session_id"])
    op.create_index("ix_assignment_recommendations_item_stable_id", "assignment_recommendations", ["item_stable_id"])
    op.create_index("ix_assignment_recommendations_team_member_id", "assignment_recommendations", ["team_member_id"])
    op.create_index("ix_assignment_recommendations_status", "assignment_recommendations", ["status"])


def downgrade() -> None:
    op.drop_table("assignment_recommendations")
    op.drop_table("leaves")