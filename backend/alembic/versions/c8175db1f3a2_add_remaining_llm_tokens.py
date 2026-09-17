"""add remaining llm tokens

Revision ID: c8175db1f3a2
Revises: be6c1a4c0fc8
"""
from alembic import op
import sqlalchemy as sa


revision = "c8175db1f3a2"
down_revision = "be6c1a4c0fc8"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("agent_executions", schema=None) as batch_op:
        batch_op.add_column(sa.Column("remaining_tokens", sa.Integer(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("agent_executions", schema=None) as batch_op:
        batch_op.drop_column("remaining_tokens")