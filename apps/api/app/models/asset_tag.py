"""业务标签与表 N:N 关联(扁平标签:平台预置 + 自定义)。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.table import Table


class AssetTag(Base):
    __tablename__ = "asset_tags"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    tables: Mapped[list["Table"]] = relationship(
        secondary="table_tags", back_populates="tags"
    )


class TableTag(Base):
    """表—标签关联(组合主键)。"""

    __tablename__ = "table_tags"

    table_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("tables.id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("asset_tags.id", ondelete="CASCADE"), primary_key=True
    )