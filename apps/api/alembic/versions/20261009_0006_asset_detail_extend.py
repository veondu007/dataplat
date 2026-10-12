"""extend asset detail: create_sql + tags + table lineage

Revision ID: 20261009_0006
Revises: 20261009_0005
Create Date: 2026-10-12
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0006"
down_revision: str | None = "20261009_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 建表语句全文
    op.add_column("tables", sa.Column("create_sql", sa.Text(), nullable=True))

    # 业务标签(预置 + 自定义)
    op.create_table(
        "asset_tags",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("name", sa.String(length=64), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    # 表 N:N 标签
    op.create_table(
        "table_tags",
        sa.Column("table_id", sa.String(length=64), sa.ForeignKey("tables.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("tag_id", sa.String(length=64), sa.ForeignKey("asset_tags.id", ondelete="CASCADE"), primary_key=True),
    )

    # 表级血缘(手动登记;真实 SQL 解析属 P1)
    op.create_table(
        "table_lineage",
        sa.Column("id", sa.String(length=64), primary_key=True),
        sa.Column("table_id", sa.String(length=64), sa.ForeignKey("tables.id", ondelete="CASCADE"), nullable=False),
        sa.Column(
            "related_table_id",
            sa.String(length=64),
            sa.ForeignKey("tables.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("direction", sa.String(length=8), nullable=False),  # upstream/downstream
        sa.Column("edge_type", sa.String(length=16), nullable=False, server_default="manual"),  # insert/select/sync/manual
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )
    op.create_index("ix_table_lineage_table", "table_lineage", ["table_id"])


def downgrade() -> None:
    op.drop_index("ix_table_lineage_table", table_name="table_lineage")
    op.drop_table("table_lineage")
    op.drop_table("table_tags")
    op.drop_table("asset_tags")
    op.drop_column("tables", "create_sql")