"""datasource_conns / sync_jobs / sync_runs: 数据源连接与同步任务

Revision ID: 20261009_0002
Revises: 20260914_0001
Create Date: 2026-10-09
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20261009_0002"
down_revision: str | None = "20260914_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "datasource_conns",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("datasource_id", sa.String(length=64), nullable=False),
        sa.Column("conn_meta", sa.JSON(), nullable=True),
        sa.Column("credentials", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["datasource_id"], ["datasources.id"]),
        sa.UniqueConstraint("datasource_id"),
    )
    op.create_table(
        "sync_jobs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("datasource_id", sa.String(length=64), nullable=False),
        sa.Column("engine", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("source_spec", sa.JSON(), nullable=True),
        sa.Column("target_database", sa.String(length=128), nullable=False),
        sa.Column("target_table", sa.String(length=128), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("max_retries", sa.Integer(), nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["datasource_id"], ["datasources.id"]),
    )
    op.create_index("ix_sync_jobs_datasource_id", "sync_jobs", ["datasource_id"])
    op.create_table(
        "sync_runs",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("sync_job_id", sa.String(length=64), nullable=False),
        sa.Column("attempt", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("rows_loaded", sa.BigInteger(), nullable=False),
        sa.Column("stream_load_label", sa.String(length=64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(["sync_job_id"], ["sync_jobs.id"]),
    )
    op.create_index("ix_sync_runs_sync_job_id", "sync_runs", ["sync_job_id"])


def downgrade() -> None:
    op.drop_index("ix_sync_runs_sync_job_id", table_name="sync_runs")
    op.drop_table("sync_runs")
    op.drop_index("ix_sync_jobs_datasource_id", table_name="sync_jobs")
    op.drop_table("sync_jobs")
    op.drop_table("datasource_conns")