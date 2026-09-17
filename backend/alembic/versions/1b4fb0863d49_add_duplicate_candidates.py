"""add duplicate candidates

Revision ID: 1b4fb0863d49
Revises: 0a3eaf752c38
"""
from alembic import op
import sqlalchemy as sa


revision = "1b4fb0863d49"
down_revision = "0a3eaf752c38"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "duplicate_candidates",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("source_stable_id", sa.String(length=50), nullable=False),
        sa.Column("target_stable_id", sa.String(length=50), nullable=False),
        sa.Column("similarity", sa.Float(), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("recommendation", sa.String(length=30), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="candidate"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("source_stable_id <> target_stable_id", name="ck_duplicate_not_self"),
        sa.CheckConstraint("similarity BETWEEN 0 AND 1", name="ck_duplicate_similarity"),
        sa.CheckConstraint("confidence BETWEEN 0 AND 1", name="ck_duplicate_confidence"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "source_stable_id", "target_stable_id", name="uq_session_duplicate_pair"),
    )
    for column in ("project_id", "session_id", "source_stable_id", "target_stable_id", "status"):
        op.create_index(f"ix_duplicate_candidates_{column}", "duplicate_candidates", [column])


def downgrade() -> None:
    op.drop_table("duplicate_candidates")