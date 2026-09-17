"""add quality and health

Revision ID: 2c50c1974e5a
Revises: 1b4fb0863d49
"""
from alembic import op
import sqlalchemy as sa


revision = "2c50c1974e5a"
down_revision = "1b4fb0863d49"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("quality_results", sa.Column("session_id", sa.String(length=36), nullable=True))
    op.create_index("ix_quality_results_session_id", "quality_results", ["session_id"])
    op.create_table(
        "board_health_results",
        sa.Column("project_id", sa.String(length=36), nullable=False),
        sa.Column("session_id", sa.String(length=36), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("risk_level", sa.String(length=20), nullable=False),
        sa.Column("metrics_json", sa.Text(), nullable=False, server_default="{}"),
        sa.Column("issues_json", sa.Text(), nullable=False, server_default="[]"),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="review_required"),
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("score BETWEEN 0 AND 100", name="ck_board_health_score"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("ix_board_health_results_project_id", "board_health_results", ["project_id"])
    op.create_index("ix_board_health_results_session_id", "board_health_results", ["session_id"], unique=True)
    op.create_index("ix_board_health_results_risk_level", "board_health_results", ["risk_level"])
    op.create_index("ix_board_health_results_status", "board_health_results", ["status"])


def downgrade() -> None:
    op.drop_table("board_health_results")
    with op.batch_alter_table("quality_results") as batch_op:
        batch_op.drop_index("ix_quality_results_session_id")
        batch_op.drop_column("session_id")