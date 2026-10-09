from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.column import Column
    from app.models.datasource import Datasource


class Table(Base):
    __tablename__ = "tables"
    __table_args__ = (UniqueConstraint("datasource_id", "database_name", "name", name="uq_tables_source_db_name"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    datasource_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasources.id"), nullable=False
    )
    database_name: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Doris 元数据同步补充字段
    num_rows: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    data_size: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 字节
    engine: Mapped[str | None] = mapped_column(String(64), nullable=True)  # 表模型 UNIQUE/DUPLICATE/AGGREGATE
    partition_cols: Mapped[str | None] = mapped_column(Text, nullable=True)  # 逗号分隔分区键
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sync_version: Mapped[int | None] = mapped_column(BigInteger, nullable=True)  # 采集批号(用于软删比对)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    datasource: Mapped["Datasource"] = relationship(back_populates="tables")
    columns: Mapped[list["Column"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )
