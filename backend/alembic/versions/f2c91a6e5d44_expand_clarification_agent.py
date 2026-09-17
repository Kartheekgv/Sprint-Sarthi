"""expand clarification agent

Revision ID: f2c91a6e5d44
Revises: e8b7f42d6a10
"""
from alembic import op
import sqlalchemy as sa


revision = "f2c91a6e5d44"
down_revision = "e8b7f42d6a10"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("clarifications", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requirement_stable_id", sa.String(length=50), nullable=False, server_default="REQ-000"))
        batch_op.add_column(sa.Column("severity", sa.String(length=20), nullable=False, server_default="medium"))
        batch_op.add_column(sa.Column("missing_field", sa.String(length=100), nullable=False, server_default="legacy_unspecified"))
        batch_op.add_column(sa.Column("recommended_answer_type", sa.String(length=30), nullable=False, server_default="single_select"))
        batch_op.add_column(sa.Column("blocking", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.create_index("ix_clarifications_requirement_stable_id", ["requirement_stable_id"], unique=False)
        batch_op.create_index("ix_clarifications_severity", ["severity"], unique=False)
        batch_op.create_index("ix_clarifications_blocking", ["blocking"], unique=False)
    op.execute(sa.text("UPDATE clarifications SET blocking = required"))
    with op.batch_alter_table("clarification_answers", schema=None) as batch_op:
        batch_op.add_column(sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    with op.batch_alter_table("clarification_answers", schema=None) as batch_op:
        batch_op.drop_column("provenance_json")
    with op.batch_alter_table("clarifications", schema=None) as batch_op:
        batch_op.drop_index("ix_clarifications_blocking")
        batch_op.drop_index("ix_clarifications_severity")
        batch_op.drop_index("ix_clarifications_requirement_stable_id")
        batch_op.drop_column("blocking")
        batch_op.drop_column("recommended_answer_type")
        batch_op.drop_column("missing_field")
        batch_op.drop_column("severity")
        batch_op.drop_column("requirement_stable_id")