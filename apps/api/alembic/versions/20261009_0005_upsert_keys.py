"""add unique constraints for tables/columns upsert keys

Revision ID: 20261009_0005
Revises: 20261009_0004
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0005"
down_revision: str | None = "20261009_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_tables_source_db_name", "tables", ["datasource_id", "database_name", "name"]
    )
    op.create_unique_constraint("uq_columns_table_name", "columns", ["table_id", "name"])


def downgrade() -> None:
    op.drop_constraint("uq_columns_table_name", "columns", type_="unique")
    op.drop_constraint("uq_tables_source_db_name", "tables", type_="unique")