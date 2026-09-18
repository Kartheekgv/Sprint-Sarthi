"""add quality clarifications

Revision ID: c21db3097ef4
Revises: 91bc27e4ad10
"""
from alembic import op
import sqlalchemy as sa


revision = "c21db3097ef4"
down_revision = "91bc27e4ad10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "quality_clarifications",
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("item_id", sa.String(length=50), nullable=False),
        sa.Column("item_type", sa.String(length=20), nullable=False),
        sa.Column("missing_fields_json", sa.Text(), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="pending"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id", "item_id", name="uq_session_quality_clarification_item"),
    )
    op.create_index("ix_quality_clarifications_session_id", "quality_clarifications", ["session_id"])
    op.create_index("ix_quality_clarifications_item_id", "quality_clarifications", ["item_id"])
    op.create_index("ix_quality_clarifications_status", "quality_clarifications", ["status"])


def downgrade() -> None:
    op.drop_index("ix_quality_clarifications_status", table_name="quality_clarifications")
    op.drop_index("ix_quality_clarifications_item_id", table_name="quality_clarifications")
    op.drop_index("ix_quality_clarifications_session_id", table_name="quality_clarifications")
    op.drop_table("quality_clarifications")