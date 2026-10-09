"""Doris DDL 连接（pymysql FE 9030）：用于建表 / TRUNCATE。数据灌入走 Stream Load（HTTP 8030）。"""

from __future__ import annotations

import pymysql

from app.core.config import settings
from app.core.exceptions import ApiError, ErrorCode


def connect_doris_ddl() -> pymysql.connections.Connection:
    try:
        return pymysql.connect(
            host=settings.doris_host,
            port=settings.doris_port,
            user=settings.doris_user,
            password=settings.doris_password,
            charset="utf8mb4",
            connect_timeout=settings.doris_connect_timeout,
        )
    except pymysql.MySQLError as exc:
        raise ApiError(
            ErrorCode.INTERNAL,
            f"无法连接 Doris 执行 DDL（{settings.doris_host}:{settings.doris_port}）: {exc}",
            status_code=503,
        ) from exc