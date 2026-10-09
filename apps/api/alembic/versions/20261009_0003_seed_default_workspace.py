"""seed default workspace: ws-default (数据源必需的工作空间外键)

Revision ID: 20261009_0003
Revises: 20261009_0002
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0003"
down_revision: str | None = "20261009_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    table = sa.table(
        "workspaces",
        sa.column("id", sa.String),
        sa.column("name", sa.String),
        sa.column("env", sa.String),
    )
    op.bulk_insert(
        table,
        [{"id": "ws-default", "name": "默认空间", "env": "dev"}],
    )


def downgrade() -> None:
    op.execute("DELETE FROM workspaces WHERE id = 'ws-default'")