"""add backlog lineage

Revision ID: b4e95a20d873
Revises: a3d84f19c762
"""
from alembic import op
import sqlalchemy as sa


revision = "b4e95a20d873"
down_revision = "a3d84f19c762"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table_name in ("epics", "user_stories", "tasks"):
        inspector = sa.inspect(op.get_bind())
        columns = {column["name"] for column in inspector.get_columns(table_name)}
        if "session_id" not in columns:
            op.add_column(table_name, sa.Column("session_id", sa.String(length=36), nullable=True))
        if "decomposition_ids_json" not in columns:
            op.add_column(table_name, sa.Column("decomposition_ids_json", sa.Text(), nullable=False, server_default="[]"))
        if "requirement_ids_json" not in columns:
            op.add_column(table_name, sa.Column("requirement_ids_json", sa.Text(), nullable=False, server_default="[]"))
        if "provenance_json" not in columns:
            op.add_column(table_name, sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"))
        indexes = {index["name"] for index in sa.inspect(op.get_bind()).get_indexes(table_name)}
        if f"ix_{table_name}_session_id" not in indexes:
            op.create_index(f"ix_{table_name}_session_id", table_name, ["session_id"])


def downgrade() -> None:
    for table_name in reversed(("epics", "user_stories", "tasks")):
        with op.batch_alter_table(table_name) as batch_op:
            batch_op.drop_index(f"ix_{table_name}_session_id")
            batch_op.drop_column("provenance_json")
            batch_op.drop_column("requirement_ids_json")
            batch_op.drop_column("decomposition_ids_json")
            batch_op.drop_column("session_id")