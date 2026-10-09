"""extend tables/columns for Doris asset sync: stats + soft delete + sync version

Revision ID: 20261009_0004
Revises: 20261009_0003
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0004"
down_revision: str | None = "20261009_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # tables: 存储 / 模型 / 分区 / 软删 / 采集批号
    op.add_column("tables", sa.Column("num_rows", sa.BigInteger(), nullable=True))
    op.add_column("tables", sa.Column("data_size", sa.BigInteger(), nullable=True))
    op.add_column("tables", sa.Column("engine", sa.String(length=64), nullable=True))
    op.add_column("tables", sa.Column("partition_cols", sa.Text(), nullable=True))
    op.add_column("tables", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("tables", sa.Column("sync_version", sa.BigInteger(), nullable=True))
    op.add_column("tables", sa.Column("last_synced_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("tables", sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    # columns: 软删 + 采集批号
    op.add_column("columns", sa.Column("is_deleted", sa.Boolean(), nullable=False, server_default=sa.text("false")))
    op.add_column("columns", sa.Column("sync_version", sa.BigInteger(), nullable=True))


def downgrade() -> None:
    op.drop_column("columns", "sync_version")
    op.drop_column("columns", "is_deleted")
    op.drop_column("tables", "created_at")
    op.drop_column("tables", "last_synced_at")
    op.drop_column("tables", "sync_version")
    op.drop_column("tables", "is_deleted")
    op.drop_column("tables", "partition_cols")
    op.drop_column("tables", "engine")
    op.drop_column("tables", "data_size")
    op.drop_column("tables", "num_rows")