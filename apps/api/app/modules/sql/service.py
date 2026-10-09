"""SQL Gateway：校验只读后，以 Doris 连接实际执行并返回结果。

当前使用平台侧统一 Doris 账号（settings.doris_*）执行；
后续接入「个人 Doris 账号绑定」后，应按工作空间用户切换连接身份（见需求 §7 安全边界）。
"""

import pymysql
from pymysql.cursors import DictCursor

from app.core.config import settings
from app.core.exceptions import ApiError, ErrorCode
from app.core.response import ok
from app.modules.sql.guard import assert_readonly

__all__ = ["execute_doris", "preview"]


def _connect() -> pymysql.connections.Connection:
    """建立到 Doris FE 的连接（MySQL 协议）。"""
    try:
        return pymysql.connect(
            host=settings.doris_host,
            port=settings.doris_port,
            user=settings.doris_user,
            password=settings.doris_password,
            database=settings.doris_database,
            charset="utf8mb4",
            connect_timeout=settings.doris_connect_timeout,
            read_timeout=60,
            cursorclass=DictCursor,
        )
    except pymysql.MySQLError as exc:
        raise ApiError(
            ErrorCode.INTERNAL,
            f"无法连接 Doris（{settings.doris_host}:{settings.doris_port}）: {exc}",
            status_code=503,
        ) from exc


def execute_doris(sql: str, limit: int = 1000) -> dict:
    """执行单条只读 SQL，返回 {columns, rows, row_count}。"""
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(sql)
            if cur.description:
                columns = [d[0] for d in cur.description]
                rows = cur.fetchmany(limit)
            else:
                columns, rows = [], []
        return {
            "columns": columns,
            "rows": rows,
            "row_count": len(rows),
            "truncated": len(rows) >= limit,
        }
    except pymysql.MySQLError as exc:
        raise ApiError(ErrorCode.INTERNAL, f"Doris 执行失败: {exc}", status_code=400) from exc
    finally:
        conn.close()


def preview(body) -> dict:
    """护栏校验 + 真实执行。"""
    assert_readonly(body.sql)
    result = execute_doris(body.sql)
    return ok(
        {
            "accepted": True,
            "sql": body.sql,
            "message": "已在 Doris 执行",
            "result": result,
        }
    )
