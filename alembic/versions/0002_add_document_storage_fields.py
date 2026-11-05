"""Add document storage location, byte size, and lifecycle state to scheme_versions.

Revision ID: 0002_storage_fields
Revises: 0001_initial_m0_schema
Create Date: 2026-11-05 14:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0002_storage_fields"
down_revision: str | None = "0001_initial_m0_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "scheme_versions",
        sa.Column("storage_path", sa.String(length=512), nullable=True),
    )
    op.add_column(
        "scheme_versions",
        sa.Column("byte_size", sa.Integer(), nullable=True),
    )
    op.add_column(
        "scheme_versions",
        sa.Column(
            "lifecycle_state",
            sa.String(length=32),
            server_default="STORED",
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("scheme_versions", "lifecycle_state")
    op.drop_column("scheme_versions", "byte_size")
    op.drop_column("scheme_versions", "storage_path")
