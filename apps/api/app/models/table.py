from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.column import Column
    from app.models.datasource import Datasource


class Table(Base):
    __tablename__ = "tables"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    datasource_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasources.id"), nullable=False
    )
    database_name: Mapped[str] = mapped_column(String(128), nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    datasource: Mapped["Datasource"] = relationship(back_populates="tables")
    columns: Mapped[list["Column"]] = relationship(
        back_populates="table", cascade="all, delete-orphan"
    )
