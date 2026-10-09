"""数据源模块的请求/响应模型。"""

from __future__ import annotations

from pydantic import BaseModel, Field


class DatasourceCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=128, description="数据源名称")
    engine: str = Field(..., description="mysql / maxcompute / xlsx")
    workspace_id: str = Field(default="ws-default", max_length=64, description="所属空间")

    # MySQL
    host: str | None = Field(default=None, max_length=255)
    port: int | None = Field(default=None, ge=1, le=65535)
    user: str | None = Field(default=None, max_length=128)
    password: str | None = Field(default=None, max_length=512)
    database: str | None = Field(default=None, max_length=128)

    # MaxCompute
    endpoint: str | None = Field(default=None, max_length=255)
    project: str | None = Field(default=None, max_length=128)
    access_id: str | None = Field(default=None, max_length=128)
    access_key: str | None = Field(default=None, max_length=512)
    jar_path: str | None = Field(default=None, max_length=512, description="ODPS JDBC jar 路径")


class DatasourceUpdate(DatasourceCreate):
    pass


class SyncRequest(BaseModel):
    source_table: str | None = Field(default=None, max_length=255, description="源表名（mysql/maxcompute）")
    sheet_name: str | None = Field(default=None, max_length=255, description="xlsx 工作表名")
    target_table: str | None = Field(default=None, max_length=128, description="目标 Doris 表名")
    target_database: str | None = Field(default=None, max_length=128, description="目标 Doris 库，默认配置库")
    max_retries: int = Field(default=2, ge=0, le=5)
    truncate: bool = Field(default=True, description="目标表已存在时 TRUNCATE")


class SyncColumnType(BaseModel):
    name: str
    doris_type: str


class TestConnection(BaseModel):
    conn_meta: dict | None = Field(default=None, description="覆盖连接参数（空则用已存）")
    credentials: dict | None = Field(default=None, description="覆盖凭证（空则用已存）")