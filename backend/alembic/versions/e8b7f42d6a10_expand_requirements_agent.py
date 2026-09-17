"""expand requirements agent

Revision ID: e8b7f42d6a10
Revises: d4a9c7102b31
"""
from alembic import op
import sqlalchemy as sa


revision = "e8b7f42d6a10"
down_revision = "d4a9c7102b31"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("requirements", schema=None) as batch_op:
        batch_op.add_column(sa.Column("requirement_status", sa.String(length=20), nullable=False, server_default="candidate"))
        batch_op.add_column(sa.Column("actors_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("systems_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("business_rules_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("constraints_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("assumptions_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("confidence", sa.Float(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("requires_clarification", sa.Boolean(), nullable=False, server_default=sa.true()))
        batch_op.add_column(sa.Column("clarification_reasons_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))
        batch_op.create_index("ix_requirements_requirement_status", ["requirement_status"], unique=False)
        batch_op.create_index("ix_requirements_requires_clarification", ["requires_clarification"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("requirements", schema=None) as batch_op:
        batch_op.drop_index("ix_requirements_requires_clarification")
        batch_op.drop_index("ix_requirements_requirement_status")
        batch_op.drop_column("provenance_json")
        batch_op.drop_column("clarification_reasons_json")
        batch_op.drop_column("requires_clarification")
        batch_op.drop_column("confidence")
        batch_op.drop_column("assumptions_json")
        batch_op.drop_column("constraints_json")
        batch_op.drop_column("business_rules_json")
        batch_op.drop_column("systems_json")
        batch_op.drop_column("actors_json")
        batch_op.drop_column("requirement_status")