"""Doris 元数据采集器：直连 FE 读 information_schema,仿 HMS connector 三方法。

连接方式与 ``app.modules.sql.service._connect`` 一致(FE MySQL 9030)。
采集使用只读账号优先;本地环境用 root。
"""

from __future__ import annotations

import time
from datetime import datetime

import pymysql

from app.core.exceptions import ApiError, ErrorCode

# Doris 内部系统库,不作为业务元数据入库
_SYSTEM_DBS = {
    "__internal_schema",
    "information_schema",
    "mysql",
}


class DorisMetadataConnector:
    def __init__(self, host: str, port: int, user: str, password: str, database: str = ""):
        self.host = host
        self.port = port
        self.user = user
        self.password = password
        self.database = database
        self.connect_timeout = 10

    def _connect(self) -> pymysql.connections.Connection:
        try:
            return pymysql.connect(
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                database=self.database or None,
                charset="utf8mb4",
                connect_timeout=self.connect_timeout,
            )
        except pymysql.MySQLError as exc:
            raise ApiError(
                ErrorCode.INTERNAL,
                f"无法连接 Doris（{self.host}:{self.port}）: {exc}",
                status_code=503,
            ) from exc

    # —— 连通性 ——

    def test_conn(self) -> dict:
        started = time.time()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT version()")
                version = cur.fetchone()[0]
            return {
                "ok": True,
                "latency_ms": int((time.time() - started) * 1000),
                "message": f"Doris {version}",
            }
        finally:
            conn.close()

    # —— 库 ——

    def list_databases(self) -> list[str]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT SCHEMA_NAME FROM information_schema.schemata "
                    "ORDER BY SCHEMA_NAME"
                )
                rows = cur.fetchall()
            out = [r[0] for r in rows if r[0] not in _SYSTEM_DBS and not r[0].startswith("__")]
            # 若配置了默认库且不在列表,补上
            if self.database and self.database not in out:
                out.append(self.database)
            return sorted(out)
        finally:
            conn.close()

    # —— 表 ——

    def list_tables(self, database: str) -> list[dict]:
        """返回某库所有表元数据。

        信息架构列(Doris 2.0 information_schema.tables):
        TABLE_NAME / TABLE_COMMENT / ENGINE / TABLE_ROWS / DATA_LENGTH /
        CREATE_TIME / UPDATE_TIME / AUTO_INCREMENT
        分区键经 SHOW CREATE 解析(P0 生产表多为分区表,信息架构无分区列)。
        """
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT TABLE_NAME, TABLE_COMMENT, ENGINE, TABLE_ROWS, DATA_LENGTH, "
                    "CREATE_TIME, UPDATE_TIME "
                    "FROM information_schema.tables "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                    "ORDER BY TABLE_NAME",
                    (database,),
                )
                rows = cur.fetchall()
            out = []
            for name, comment, engine, num_rows, data_len, create_time, update_time in rows:
                out.append(
                    {
                        "database_name": database,
                        "name": name,
                        "comment": comment,
                        "engine": engine,  # 表模型 UNIQUE/DUPLICATE/AGGREGATE
                        "num_rows": _to_int(num_rows),
                        "data_size": _to_int(data_len),
                        "create_time": _to_datetime(create_time),
                        "update_time": _to_datetime(update_time),
                    }
                )
            return out
        finally:
            conn.close()

    # —— 列 + 分区键 ——

    def list_columns(self, database: str, table: str) -> list[dict]:
        """返回表列定义,并解析分区键(信息架构无分区列,用 SHOW CREATE 提取)。"""
        conn = self._connect()
        try:
            partition_cols = self._partition_keys(database, table)
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COLUMN_NAME, DATA_TYPE, ORDINAL_POSITION, "
                    "COALESCE(COLUMN_COMMENT, ''), IS_NULLABLE, CHARACTER_MAXIMUM_LENGTH "
                    "FROM information_schema.columns "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s "
                    "ORDER BY ORDINAL_POSITION",
                    (database, table),
                )
                rows = cur.fetchall()
            out = []
            for idx, (name, dtype, pos, comment, nullable, charlen) in enumerate(rows, start=1):
                full_type = _full_type(dtype, charlen)
                out.append(
                    {
                        "name": name,
                        "data_type": full_type,
                        "position": pos or idx,
                        "is_partition": name in partition_cols,
                        "comment": comment or None,
                    }
                )
            return out
        finally:
            conn.close()

    def _partition_keys(self, database: str, table: str) -> set[str]:
        """从 SHOW CREATE TABLE 解析分区键列名,解析失败回退空集。"""
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(f"SHOW CREATE TABLE `{database}`.`{table}`")
                row = cur.fetchone()
            if not row:
                return set()
            ddl = row[0] if isinstance(row, tuple) else str(row[0] if row else "")
            return _extract_partition_keys(ddl)
        except Exception:
            return set()
        finally:
            conn.close()


def _to_int(v) -> int | None:
    if v is None:
        return None
    try:
        return int(v) if str(v) else 0
    except (TypeError, ValueError):
        return None


def _to_datetime(v) -> datetime | None:
    """Doris 时间原样返回即可(pymysql 已转为 datetime);空/0 返回 None。"""
    if v is None or v == 0 or str(v) == "0000-00-00 00:00:00":
        return None
    return v


def _full_type(dtype: str, charlen) -> str:
    if dtype in ("VARCHAR", "CHAR") and charlen:
        return f"{dtype}({charlen})"
    if dtype in ("DECIMAL",):
        return dtype
    return dtype


def _extract_partition_keys(ddl: str) -> set[str]:
    """从 `PARTITION BY RANGE/LIST [COLUMNS] (...)` 提取列名。"""
    import re

    keys: set[str] = set()
    # PARTITION BY RANGE(...) / LIST(...) / RANGE COLUMNS(a,b) / LIST COLUMNS(a,b)
    # 兼容带 `xxx` 反引号或单/双引号标识符
    for m in re.finditer(
        r"PARTITION BY\s+(?:RANGE|LIST)\s*(?:COLUMNS\s*)?\(([^)]*)\)", ddl, re.IGNORECASE
    ):
        names = [n.strip().strip("`\"'") for n in m.group(1).split(",") if n.strip()]
        keys.update(names)
    return {k for k in keys if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", k)}


__all__ = ["DorisMetadataConnector", "_extract_partition_keys"]