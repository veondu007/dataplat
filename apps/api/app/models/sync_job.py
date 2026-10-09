"""数据导入 Doris 的同步任务。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.sync_run import SyncRun


class SyncJob(Base):
    __tablename__ = "sync_jobs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    datasource_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasources.id"), nullable=False
    )
    engine: Mapped[str] = mapped_column(String(32), nullable=False)  # mysql/maxcompute/xlsx
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="pending")
    # 源表 / sheet + 推断列定义
    source_spec: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    target_database: Mapped[str] = mapped_column(String(128), nullable=False)
    target_table: Mapped[str] = mapped_column(String(128), nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    max_retries: Mapped[int] = mapped_column(Integer, nullable=False, default=2)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    runs: Mapped[list["SyncRun"]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )