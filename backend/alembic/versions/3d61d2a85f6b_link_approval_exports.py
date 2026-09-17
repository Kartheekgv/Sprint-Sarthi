"""link approval exports

Revision ID: 3d61d2a85f6b
Revises: 2c50c1974e5a
"""
from alembic import op
import sqlalchemy as sa


revision = "3d61d2a85f6b"
down_revision = "2c50c1974e5a"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("approvals", sa.Column("session_id", sa.String(length=36), nullable=True))
    op.create_index("ix_approvals_session_id", "approvals", ["session_id"])
    op.add_column("exports", sa.Column("session_id", sa.String(length=36), nullable=True))
    op.create_index("ix_exports_session_id", "exports", ["session_id"])


def downgrade() -> None:
    with op.batch_alter_table("exports") as batch_op:
        batch_op.drop_index("ix_exports_session_id")
        batch_op.drop_column("session_id")
    with op.batch_alter_table("approvals") as batch_op:
        batch_op.drop_index("ix_approvals_session_id")
        batch_op.drop_column("session_id")