"""add estimation rationale

Revision ID: c5fa6b31e984
Revises: b4e95a20d873
"""
from alembic import op
import sqlalchemy as sa


revision = "c5fa6b31e984"
down_revision = "b4e95a20d873"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "user_stories",
        sa.Column("estimation_rationale", sa.Text(), nullable=False, server_default=""),
    )
    op.add_column(
        "tasks",
        sa.Column("estimation_rationale", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_column("estimation_rationale")
    with op.batch_alter_table("user_stories") as batch_op:
        batch_op.drop_column("estimation_rationale")