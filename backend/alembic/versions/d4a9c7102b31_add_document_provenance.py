"""add document provenance

Revision ID: d4a9c7102b31
Revises: c8175db1f3a2
"""
from alembic import op
import sqlalchemy as sa


revision = "d4a9c7102b31"
down_revision = "c8175db1f3a2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.add_column(sa.Column("document_code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("language", sa.String(length=20), nullable=False, server_default="unknown"))
        batch_op.add_column(sa.Column("warnings_json", sa.Text(), nullable=False, server_default="[]"))
        batch_op.add_column(sa.Column("extraction_confidence", sa.Float(), nullable=True))
    connection = op.get_bind()
    project_ids = [row[0] for row in connection.execute(sa.text("SELECT DISTINCT project_id FROM documents"))]
    for project_id in project_ids:
        rows = connection.execute(
            sa.text("SELECT id FROM documents WHERE project_id = :project_id ORDER BY created_at, id"),
            {"project_id": project_id},
        )
        for position, row in enumerate(rows, 1):
            connection.execute(
                sa.text("UPDATE documents SET document_code = :code WHERE id = :id"),
                {"code": f"DOC-{position:03d}", "id": row[0]},
            )
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.alter_column("document_code", existing_type=sa.String(length=50), nullable=False)
        batch_op.create_unique_constraint("uq_project_document_code", ["project_id", "document_code"])

    with op.batch_alter_table("document_sections", schema=None) as batch_op:
        batch_op.add_column(sa.Column("chunk_code", sa.String(length=50), nullable=True))
        batch_op.add_column(sa.Column("token_count", sa.Integer(), nullable=False, server_default="0"))
        batch_op.add_column(sa.Column("extraction_confidence", sa.Float(), nullable=False, server_default="1.0"))
        batch_op.add_column(sa.Column("metadata_json", sa.Text(), nullable=False, server_default="{}"))
    document_ids = [row[0] for row in connection.execute(sa.text("SELECT DISTINCT document_id FROM document_sections"))]
    for document_id in document_ids:
        rows = connection.execute(
            sa.text("SELECT id, content FROM document_sections WHERE document_id = :document_id ORDER BY chunk_index, id"),
            {"document_id": document_id},
        )
        for position, row in enumerate(rows, 1):
            connection.execute(
                sa.text("UPDATE document_sections SET chunk_code = :code, token_count = :tokens WHERE id = :id"),
                {"code": f"CHUNK-{position:03d}", "tokens": len(row[1].split()), "id": row[0]},
            )
    with op.batch_alter_table("document_sections", schema=None) as batch_op:
        batch_op.alter_column("chunk_code", existing_type=sa.String(length=50), nullable=False)
        batch_op.create_unique_constraint("uq_document_chunk_code", ["document_id", "chunk_code"])


def downgrade() -> None:
    with op.batch_alter_table("document_sections", schema=None) as batch_op:
        batch_op.drop_constraint("uq_document_chunk_code", type_="unique")
        batch_op.drop_column("metadata_json")
        batch_op.drop_column("extraction_confidence")
        batch_op.drop_column("token_count")
        batch_op.drop_column("chunk_code")
    with op.batch_alter_table("documents", schema=None) as batch_op:
        batch_op.drop_constraint("uq_project_document_code", type_="unique")
        batch_op.drop_column("extraction_confidence")
        batch_op.drop_column("warnings_json")
        batch_op.drop_column("language")
        batch_op.drop_column("document_code")