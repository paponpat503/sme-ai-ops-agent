"""Add tenant-scoped pgvector document chunks."""

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    if op.get_bind().dialect.name != "postgresql":
        return
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.execute(
        """
        CREATE TABLE document_chunks (
            tenant_id varchar(80) NOT NULL,
            doc_id varchar(160) NOT NULL,
            source varchar(255) NOT NULL,
            section varchar(255) NOT NULL,
            version varchar(64) NOT NULL,
            content text NOT NULL,
            embedding vector(1536) NOT NULL,
            PRIMARY KEY (tenant_id, doc_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_tenant ON document_chunks (tenant_id)"
    )
    op.execute(
        "CREATE INDEX ix_document_chunks_embedding_hnsw ON document_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    if op.get_bind().dialect.name == "postgresql":
        op.execute("DROP TABLE IF EXISTS document_chunks")
