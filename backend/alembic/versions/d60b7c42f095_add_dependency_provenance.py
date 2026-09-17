"""add dependency provenance

Revision ID: d60b7c42f095
Revises: c5fa6b31e984
"""
from alembic import op
import sqlalchemy as sa


revision = "d60b7c42f095"
down_revision = "c5fa6b31e984"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("dependencies", sa.Column("session_id", sa.String(length=36), nullable=True))
    op.add_column("dependencies", sa.Column("confidence", sa.Float(), nullable=False, server_default="0"))
    op.add_column("dependencies", sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))
    op.create_index("ix_dependencies_session_id", "dependencies", ["session_id"])


def downgrade() -> None:
    with op.batch_alter_table("dependencies") as batch_op:
        batch_op.drop_index("ix_dependencies_session_id")
        batch_op.drop_column("provenance_json")
        batch_op.drop_column("confidence")
        batch_op.drop_column("session_id")