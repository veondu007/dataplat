"""MySQL 引擎：基于 pymysql 直读源库。

连接参数来自 datasource_conns：conn_meta 含 host/port/database，credentials 含 user/password。
"""

from __future__ import annotations

import time

import pymysql
from pymysql.cursors import Cursor

from app.core.exceptions import ApiError, ErrorCode
from app.modules.datasource.sync.engines.base import BaseEngine, EngineColumn, EngineTable


class MySQLEngine(BaseEngine):
    def __init__(self, meta: dict, credentials: dict):
        self.host = meta.get("host", "127.0.0.1")
        self.port = int(meta.get("port", 3306))
        self.database = meta.get("database", "")
        self.user = credentials.get("user", "")
        self.password = credentials.get("password", "")
        self.connect_timeout = int(meta.get("connect_timeout", 10))

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
            raise ApiError(ErrorCode.INTERNAL, f"无法连接 MySQL（{self.host}:{self.port}）: {exc}", status_code=400) from exc

    def test_conn(self) -> dict:
        started = time.time()
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT VERSION()")
                version = cur.fetchone()[0]
            return {"ok": True, "latency_ms": int((time.time() - started) * 1000), "message": f"MySQL {version}"}
        finally:
            conn.close()

    def list_tables(self) -> list[EngineTable]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT TABLE_SCHEMA, TABLE_NAME, COALESCE(TABLE_COMMENT, '') "
                    "FROM information_schema.TABLES "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_TYPE = 'BASE TABLE' "
                    "ORDER BY TABLE_NAME",
                    (self.database,),
                )
                rows = cur.fetchall()
            return [
                EngineTable(database_name=r[0], name=r[1], comment=r[2] or None) for r in rows
            ]
        finally:
            conn.close()

    def columns(self, table: str) -> list[EngineColumn]:
        conn = self._connect()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT COLUMN_NAME, DATA_TYPE, COALESCE(CHARACTER_MAXIMUM_LENGTH, 0) "
                    "FROM information_schema.COLUMNS "
                    "WHERE TABLE_SCHEMA = %s AND TABLE_NAME = %s ORDER BY ORDINAL_POSITION",
                    (self.database, table),
                )
                rows = cur.fetchall()
            if not rows:
                raise ApiError(ErrorCode.NOT_FOUND, f"MySQL 表中不存在: {self.database}.{table}", status_code=404)
            cols: list[EngineColumn] = []
            for name, dtype, charlen in rows:
                if dtype in ("varchar", "char", "text") and charlen:
                    native = f"{dtype}({charlen})" if charlen <= 65535 else "longtext"
                else:
                    native = dtype
                cols.append(EngineColumn(name=name, source_type=native))
            return cols
        finally:
            conn.close()

    def read_rows(self, table: str, batch_size: int = 1000):
        conn = self._connect()
        cur: Cursor | None = None
        try:
            cur = conn.cursor()
            qtable = table.replace("`", "``")
            cur.execute(f"SELECT * FROM `{self.database}`.`{qtable}`")
            while True:
                batch = cur.fetchmany(batch_size)
                if not batch:
                    break
                yield [list(row) for row in batch]
        finally:
            if cur is not None:
                cur.close()
            conn.close()