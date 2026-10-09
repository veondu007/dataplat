"""同步任务的重试运行历史（1 次提交 = 多次 attempt）。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.sync_job import SyncJob


class SyncRun(Base):
    __tablename__ = "sync_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    sync_job_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sync_jobs.id"), nullable=False
    )
    attempt: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 起
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    rows_loaded: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    stream_load_label: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    job: Mapped["SyncJob"] = relationship(back_populates="runs")