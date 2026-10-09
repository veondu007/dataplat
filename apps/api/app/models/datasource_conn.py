"""数据源连接信息（1:1 与 datasources，隔离敏感凭证）。"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import DateTime, ForeignKey, JSON, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.datasource import Datasource


class DatasourceConn(Base):
    __tablename__ = "datasource_conns"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    datasource_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("datasources.id"), nullable=False, unique=True
    )
    # 非敏感连接信息：host / port / database / project / endpoint / file_path / sheet 等
    conn_meta: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    # 敏感凭证：password / access_key。P0 明文；TODO: AES-GCM(KEY derived from DATAPLAT_SECRET)
    credentials: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now()
    )

    datasource: Mapped["Datasource"] = relationship(back_populates="conn")