"""表级数据血缘(手动登记;位预留,真实 SQL 解析属 P1)。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.table import Table


class TableLineage(Base):
    __tablename__ = "table_lineage"
    __table_args__ = (Index("ix_table_lineage_table", "table_id"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    table_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False
    )
    related_table_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tables.id", ondelete="CASCADE"), nullable=False
    )
    direction: Mapped[str] = mapped_column(String(8), nullable=False)  # upstream/downstream
    edge_type: Mapped[str] = mapped_column(String(16), nullable=False, default="manual")  # insert/select/sync/manual
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    table: Mapped["Table"] = relationship(foreign_keys=[table_id], back_populates="lineage")
    related_table: Mapped["Table"] = relationship(foreign_keys=[related_table_id])