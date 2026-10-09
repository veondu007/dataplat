"""MaxCompute 引擎：通过 ODPS JDBC 驱动直连。

需要：
- `pip install jaydebeapi`
- ODPS JDBC jar（com.aliyun.odps:odps-jdbc），路径由 conn_meta["jar_path"] 配置

连接串：`jdbc:odps:https://{endpoint}?project={project}`，认证 access_id / access_key。
credentials 含 access_id / access_key；conn_meta 含 endpoint / project / jar_path。

若 jaydebeapi 或 jar 不可用，抛出明确的引导错误（P0 降级路径见实现计划：登记+连通可用于
元数据，实际同步需补齐 JDBC 环境）。
"""

from __future__ import annotations

import os
import time

from app.core.exceptions import ApiError, ErrorCode
from app.modules.datasource.sync.engines.base import BaseEngine, EngineColumn, EngineTable


def _load_jdbc():
    try:
        import jaydebeapi  # type: ignore
    except ImportError:
        raise ApiError(
            ErrorCode.INTERNAL,
            "MaxCompute 同步需要 jaydebeapi：请先 `pip install jaydebeapi`，"
            "并在数据源 conn_meta.jar_path 配置 ODPS JDBC jar 路径",
            status_code=400,
        ) from None
    return jaydebeapi


class MaxComputeEngine(BaseEngine):
    def __init__(self, meta: dict, credentials: dict):
        self.endpoint = meta.get("endpoint", "")
        self.project = meta.get("project", "")
        self.jar_path = meta.get("jar_path", "")
        self.access_id = credentials.get("access_id", "")
        self.access_key = credentials.get("access_key", "")

    def _url(self) -> str:
        return f"jdbc:odps:https://{self.endpoint}?project={self.project}"

    def _connect(self):
        jd = _load_jdbc()
        if not self.jar_path or not os.path.exists(self.jar_path):
            raise ApiError(
                ErrorCode.INTERNAL,
                f"MaxCompute JDBC jar 不存在: {self.jar_path}（请在数据源配置 jar_path）",
                status_code=400,
            )
        jdbc_user = f"{self.access_id}:{self.access_key}"
        try:
            return jd.connect(
                self._url(),
                [jdbc_user, ""],
                jars=[self.jar_path],
                driver_args={"odps.service.ignore.unknown": "true"},
            )
        except Exception as exc:
            raise ApiError(ErrorCode.INTERNAL, f"连接 MaxCompute 失败: {exc}", status_code=400) from exc

    def test_conn(self) -> dict:
        started = time.time()
        _load_jdbc()
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.fetchone()
            cur.close()
            return {
                "ok": True,
                "latency_ms": int((time.time() - started) * 1000),
                "message": f"MaxCompute 项目 {self.project} 连接成功",
            }
        except Exception as exc:
            return {"ok": False, "latency_ms": int((time.time() - started) * 1000), "message": str(exc)}
        finally:
            conn.close()

    def list_tables(self) -> list[EngineTable]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute("SHOW TABLES")
            rows = cur.fetchall()
            cur.close()
            out: list[EngineTable] = []
            for row in rows:
                name = str(row[0]) if row else ""
                if name and not name.startswith("__"):
                    out.append(EngineTable(database_name=self.project, name=name))
            return out
        finally:
            conn.close()

    def columns(self, table: str) -> list[EngineColumn]:
        conn = self._connect()
        try:
            cur = conn.cursor()
            cur.execute(f"DESCRIBE `{table}`")
            rows = cur.fetchall()
            cur.close()
            cols: list[EngineColumn] = []
            for row in rows:
                if not row or not row[0]:
                    continue
                name, dtype = str(row[0]), str(row[1])
                if dtype.lower() in ("partition", "zone"):
                    break
                cols.append(EngineColumn(name=name, source_type=dtype))
            if not cols:
                raise ApiError(ErrorCode.NOT_FOUND, f"MaxCompute 表无列或不存在: {table}", status_code=404)
            return cols
        finally:
            conn.close()

    def read_rows(self, table: str, batch_size: int = 1000):
        """分页读取整表。P0 用 ORDER BY 稳定顺序 + LIMIT/OFFSET；数据量大时建议后续改 Tunnel。"""
        conn = self._connect()
        try:
            offset = 0
            while True:
                cur = conn.cursor()
                cur.execute(f"SELECT * FROM `{table}` LIMIT {batch_size} OFFSET {offset}")
                batch = cur.fetchall()
                cur.close()
                if not batch:
                    break
                rows = [list(r) for r in batch]
                yield rows
                offset += len(rows)
        finally:
            conn.close()