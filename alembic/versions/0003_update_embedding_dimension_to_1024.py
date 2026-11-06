"""Update scheme_knowledge_chunks embedding vector dimension to 1024 for BAAI/bge-m3.

Revision ID: 0003_bge_m3_1024
Revises: 0002_storage_fields
Create Date: 2026-11-06 14:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003_bge_m3_1024"
down_revision: str | None = "0002_storage_fields"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        # 1. Drop existing HNSW index tied to 1536-dimensional vectors
        op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_embedding")

        # 2. Truncate stale chunks from previous pseudo-embedder to allow column type alteration
        op.execute("TRUNCATE TABLE scheme_knowledge_chunks CASCADE")

        # 3. Alter column type to vector(1024) for BAAI/bge-m3
        op.execute("ALTER TABLE scheme_knowledge_chunks ALTER COLUMN embedding TYPE vector(1024)")

        # 4. Rebuild HNSW index with vector_cosine_ops for 1024 dimensions
        op.execute(
            "CREATE INDEX idx_knowledge_chunks_embedding ON scheme_knowledge_chunks "
            "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )

        # 5. Ensure GIN full-text search index on to_tsvector('english', chunk_content) exists
        op.execute(
            "CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_fts ON scheme_knowledge_chunks "
            "USING GIN(to_tsvector('english', chunk_content))"
        )
    else:
        # SQLite / other fallback dialects use JSON text storage via FlexibleVector
        pass


def downgrade() -> None:
    bind = op.get_bind()
    dialect_name = bind.dialect.name

    if dialect_name == "postgresql":
        op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_embedding")
        op.execute("TRUNCATE TABLE scheme_knowledge_chunks CASCADE")
        op.execute("ALTER TABLE scheme_knowledge_chunks ALTER COLUMN embedding TYPE vector(1536)")
        op.execute(
            "CREATE INDEX idx_knowledge_chunks_embedding ON scheme_knowledge_chunks "
            "USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
        )
