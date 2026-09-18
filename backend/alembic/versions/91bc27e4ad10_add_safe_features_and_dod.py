"""add safe features and definition of done

Revision ID: 91bc27e4ad10
Revises: 6a29d78c041e
"""
from alembic import op
import sqlalchemy as sa


revision = "91bc27e4ad10"
down_revision = "6a29d78c041e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("epics") as batch_op:
        batch_op.add_column(sa.Column("architecture_layer", sa.String(length=200), nullable=False, server_default="Legacy / unspecified"))
    op.create_table(
        "features",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=True),
        sa.Column("epic_id", sa.String(length=36), nullable=False),
        sa.Column("stable_id", sa.String(length=50), nullable=False),
        sa.Column("decomposition_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("requirement_ids_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("title", sa.String(length=500), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("business_value", sa.Text(), nullable=False, server_default=""),
        sa.Column("source_references_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("provenance_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="draft"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["epic_id"], ["epics.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("stable_id"),
    )
    op.create_index("ix_features_project_id", "features", ["project_id"])
    op.create_index("ix_features_session_id", "features", ["session_id"])
    op.create_index("ix_features_epic_id", "features", ["epic_id"])
    with op.batch_alter_table("user_stories") as batch_op:
        batch_op.add_column(sa.Column("feature_id", sa.String(length=36), nullable=True))
        batch_op.add_column(sa.Column("definition_of_done_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.create_foreign_key("fk_user_stories_feature", "features", ["feature_id"], ["id"], ondelete="CASCADE")
        batch_op.create_index("ix_user_stories_feature_id", ["feature_id"])
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.add_column(sa.Column("work_category", sa.String(length=30), nullable=False, server_default="functional"))
        batch_op.add_column(sa.Column("acceptance_criteria_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("definition_of_done_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.create_index("ix_tasks_work_category", ["work_category"])


def downgrade() -> None:
    with op.batch_alter_table("tasks") as batch_op:
        batch_op.drop_index("ix_tasks_work_category")
        batch_op.drop_column("definition_of_done_json")
        batch_op.drop_column("acceptance_criteria_json")
        batch_op.drop_column("work_category")
    with op.batch_alter_table("user_stories") as batch_op:
        batch_op.drop_index("ix_user_stories_feature_id")
        batch_op.drop_constraint("fk_user_stories_feature", type_="foreignkey")
        batch_op.drop_column("definition_of_done_json")
        batch_op.drop_column("feature_id")
    op.drop_index("ix_features_epic_id", table_name="features")
    op.drop_index("ix_features_session_id", table_name="features")
    op.drop_index("ix_features_project_id", table_name="features")
    op.drop_table("features")
    with op.batch_alter_table("epics") as batch_op:
        batch_op.drop_column("architecture_layer")