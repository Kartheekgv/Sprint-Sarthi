"""add decomposition agent

Revision ID: a3d84f19c762
Revises: f2c91a6e5d44
"""
from alembic import op
import sqlalchemy as sa


revision = "a3d84f19c762"
down_revision = "f2c91a6e5d44"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "decompositions",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("stable_id", sa.String(length=50), nullable=False),
        sa.Column("requirement_ids_json", sa.Text(), nullable=False),
        sa.Column("parent_capability", sa.String(length=300), nullable=False),
        sa.Column("component_type", sa.String(length=30), nullable=False),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("suggested_backlog_level", sa.String(length=20), nullable=False),
        sa.Column("rationale", sa.Text(), nullable=False),
        sa.Column("source_references_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["session_id"], ["analysis_sessions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("project_id", "stable_id", name="uq_project_decomposition_stable_id"),
    )
    op.create_index("ix_decompositions_project_id", "decompositions", ["project_id"])
    op.create_index("ix_decompositions_session_id", "decompositions", ["session_id"])
    op.create_index("ix_decompositions_component_type", "decompositions", ["component_type"])
    op.create_index("ix_decompositions_suggested_backlog_level", "decompositions", ["suggested_backlog_level"])
    op.create_index("ix_decompositions_status", "decompositions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_decompositions_status", table_name="decompositions")
    op.drop_index("ix_decompositions_suggested_backlog_level", table_name="decompositions")
    op.drop_index("ix_decompositions_component_type", table_name="decompositions")
    op.drop_index("ix_decompositions_session_id", table_name="decompositions")
    op.drop_index("ix_decompositions_project_id", table_name="decompositions")
    op.drop_table("decompositions")