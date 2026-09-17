"""expand planning data

Revision ID: e71c8d530a16
Revises: d60b7c42f095
"""
from alembic import op
import sqlalchemy as sa


revision = "e71c8d530a16"
down_revision = "d60b7c42f095"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("departments", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.add_column("team_members", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.add_column("team_members", sa.Column("role", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("team_members", sa.Column("capacity_hours", sa.Float(), nullable=True))
    op.add_column("team_members", sa.Column("allocation_percent", sa.Float(), nullable=False, server_default="100"))
    op.add_column("team_members", sa.Column("location", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("team_members", sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))
    op.add_column("holidays", sa.Column("location", sa.String(length=150), nullable=False, server_default=""))
    op.add_column("holidays", sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))
    op.add_column("sprints", sa.Column("external_id", sa.String(length=100), nullable=True))
    op.add_column("sprints", sa.Column("capacity_points", sa.Float(), nullable=True))
    op.add_column("sprints", sa.Column("committed_points", sa.Float(), nullable=False, server_default="0"))
    op.add_column("sprints", sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))


def downgrade() -> None:
    for table_name, columns in (
        ("sprints", ("provenance_json", "committed_points", "capacity_points", "external_id")),
        ("holidays", ("provenance_json", "location")),
        ("team_members", ("provenance_json", "location", "allocation_percent", "capacity_hours", "role", "external_id")),
        ("departments", ("external_id",)),
    ):
        with op.batch_alter_table(table_name) as batch_op:
            for column in columns:
                batch_op.drop_column(column)