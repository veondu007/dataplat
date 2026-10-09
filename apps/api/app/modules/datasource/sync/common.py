"""同步公共能力：类型映射、Doris DDL 生成、Stream Load 客户端。"""

from __future__ import annotations

import io
import time
from dataclasses import dataclass
from datetime import date as _date
from datetime import datetime as _dt

import requests

from app.core.config import settings
from app.core.exceptions import ApiError, ErrorCode

# —— 类型映射（源 → Doris） ——

MYSQL_TO_DORIS = {
    "tinyint": "TINYINT",
    "smallint": "SMALLINT",
    "mediumint": "INT",
    "int": "INT",
    "integer": "INT",
    "bigint": "BIGINT",
    "float": "FLOAT",
    "double": "DOUBLE",
    "real": "DOUBLE",
    "decimal": "DECIMAL",
    "numeric": "DECIMAL",
    "date": "DATEV2",
    "datetime": "DATETIME",
    "timestamp": "DATETIME",
    "time": "VARCHAR(32)",
    "year": "INT",
    "char": "CHAR",
    "varchar": "VARCHAR",
    "tinytext": "VARCHAR(255)",
    "text": "VARCHAR(65533)",
    "mediumtext": "VARCHAR(65533)",
    "longtext": "VARCHAR(65533)",
    "tinyblob": "VARCHAR(255)",
    "blob": "VARCHAR(65533)",
    "mediumblob": "VARCHAR(65533)",
    "longblob": "VARCHAR(65533)",
    "json": "VARCHAR(65533)",
    "bool": "BOOLEAN",
    "boolean": "BOOLEAN",
    "bit": "BOOLEAN",
    "enum": "VARCHAR(65533)",
    "set": "VARCHAR(65533)",
}

MAXCOMPUTE_TO_DORIS = {
    "string": "VARCHAR(65533)",
    "varchar": "VARCHAR",
    "char": "CHAR",
    "bigint": "BIGINT",
    "smallint": "SMALLINT",
    "int": "INT",
    "tinyint": "TINYINT",
    "double": "DOUBLE",
    "float": "FLOAT",
    "decimal": "DECIMAL",
    "boolean": "BOOLEAN",
    "datetime": "DATETIME",
    "timestamp": "DATETIME",
    "date": "DATEV2",
    "array": "VARCHAR(65533)",
    "map": "VARCHAR(65533)",
    "struct": "VARCHAR(65533)",
}


def _map_decimal(src_type: str) -> str:
    """DECIMAL(p,s) / NUMERIC(p,s) 保留精度。"""
    lowered = src_type.lower()
    if lowered.startswith(("decimal", "numeric")) and "(" in lowered:
        return "DECIMAL" + lowered[lowered.index("("):]
    return "DECIMAL"


def mysql_to_doris(src_type: str) -> str:
    """MySQL 类型 → Doris 类型。"""
    lowered = src_type.lower()
    if lowered.startswith(("decimal", "numeric")):
        return _map_decimal(lowered)
    for prefix, doris in (("varchar", "VARCHAR"), ("char", "CHAR")):
        if lowered.startswith(prefix) and "(" in lowered:
            return doris + lowered[lowered.index("("):]
    base = lowered.split("(")[0].split(" ")[0].split("unsigned")[0]
    return MYSQL_TO_DORIS.get(base, "VARCHAR(65533)")


def maxcompute_to_doris(src_type: str) -> str:
    """MaxCompute 类型 → Doris 类型。"""
    lowered = src_type.lower()
    if lowered.startswith(("decimal", "numeric")):
        return _map_decimal(lowered)
    if lowered.startswith(("varchar", "char")) and "(" in lowered:
        prefix = "VARCHAR" if lowered.startswith("varchar") else "CHAR"
        return prefix + lowered[lowered.index("("):]
    return MAXCOMPUTE_TO_DORIS.get(lowered, "VARCHAR(65533)")


# —— xlsx 单元格类型推断 ——

@dataclass
class InferredColumn:
    name: str
    doris_type: str


def _is_int(v) -> bool:
    return isinstance(v, bool) is False and isinstance(v, int)


def _is_float(v) -> bool:
    return isinstance(v, float) or (isinstance(v, int) and not _is_int(v))


def infer_xlsx_columns(header_row: list, sample_rows: list[list], n_sample: int = 100) -> list[InferredColumn]:
    """根据多行样例推断列类型（全 int→BIGINT，float→DOUBLE，bool→BOOLEAN，date→DATETIME，否则 VARCHAR）。

    header_row 为列名；sample_rows 为不含表头的数据行。列多于表头时补名。
    """
    ncols = max(len(header_row), max((len(r) for r in sample_rows), default=0))
    cols: list[InferredColumn] = []
    for i in range(ncols):
        col_name = str(header_row[i]) if i < len(header_row) else f"col_{i + 1}"
        values = [r[i] for r in sample_rows[:n_sample] if i < len(r) and r[i] is not None]
        doris_type = "VARCHAR(65533)"
        if values:
            if all(type(v) is bool for v in values):
                doris_type = "BOOLEAN"
            elif all(_is_int(v) for v in values):
                doris_type = "BIGINT"
            elif all(isinstance(v, (int, float)) for v in values):
                doris_type = "DOUBLE"
            elif all(isinstance(v, (_date, _dt)) for v in values):
                doris_type = "DATETIME"
        cols.append(InferredColumn(name=col_name, doris_type=doris_type))
    return cols


# —— Doris DDL ——

def _quote_ident(name: str) -> str:
    return f"`{name}`"


def doris_ddl(database: str, table: str, columns: list[InferredColumn]) -> str:
    """生成 Doris 建表 DDL。用首列作 UNIQUE KEY 与分桶键，BUCKETS 8，副本数 2。

    表名/列名已由 guard 校验为合法标识符，此处仍加反引号防护。
    """
    if not columns:
        raise ApiError(ErrorCode.VALIDATION, "目标表至少需要 1 列", status_code=400)
    cols_sql = ",\n        ".join(
        f"{_quote_ident(c.name)} {c.doris_type}" for c in columns
    )
    key_col = _quote_ident(columns[0].name)
    return (
        f"CREATE TABLE IF NOT EXISTS `{database}`.`{table}` (\n"
        f"        {cols_sql}\n"
        f"    )\n"
        f"    UNIQUE KEY ({key_col})\n"
        f"    DISTRIBUTED BY HASH ({key_col}) BUCKETS 8\n"
        f'    PROPERTIES ("replication_num" = "2")'
    )


# —— Stream Load 客户端 ——

@dataclass
class StreamLoadResult:
    status: str
    loaded_rows: int
    total_rows: int
    message: str
    label: str


def stream_load(
    database: str,
    table: str,
    csv_bytes: bytes,
    label: str,
    columns: list[InferredColumn],
) -> StreamLoadResult:
    """通过 Doris Stream Load（FE HTTP 8030，307 到 BE）灌入 CSV。

    format=csv_with_names：首行即列名，Doris 按列名映射；**columns** 仅作顺序提示。
    """
    url = f"http://{settings.doris_host}:{settings.doris_http_port}/api/{database}/{table}/_stream_load"
    headers = {
        "Expect": "100-continue",
        "column_separator": ",",
        "label": label,
        "format": "csv_with_names",
        "columns": ",".join(_quote_ident(c.name) for c in columns),
    }
    auth = (settings.doris_user, settings.doris_password)
    try:
        resp = requests.put(url, data=csv_bytes, headers=headers, auth=auth, timeout=600)
    except requests.RequestException as exc:
        raise ApiError(ErrorCode.INTERNAL, f"Doris Stream Load 请求失败: {exc}", status_code=502) from exc

    payload = resp.json() if resp.headers.get("Content-Type", "").startswith("application/json") else {}
    if str(resp.status_code).startswith("30"):
        # FE 307 重定向到 BE：跟随 Location 再 PUT 一次
        loc = resp.headers.get("Location")
        if not loc:
            raise ApiError(ErrorCode.INTERNAL, "Doris 重定向但缺少 Location", status_code=502)
        try:
            resp = requests.put(loc, data=csv_bytes, headers=headers, auth=auth, timeout=600)
            payload = (
                resp.json()
                if resp.headers.get("Content-Type", "").startswith("application/json")
                else {}
            )
        except requests.RequestException as exc:
            raise ApiError(ErrorCode.INTERNAL, f"Doris Stream Load 重定向请求失败: {exc}", status_code=502) from exc

    status = payload.get("Status", "UNKNOWN")
    ok_flag = status.upper() in ("SUCCESS", "OK")
    loaded = int(payload.get("NumberLoadedRows", 0) or 0)
    total = int(payload.get("NumberTotalRows", 0) or 0)
    msg = payload.get("Message", "") or payload.get("ErrorURL", "") or status
    if not ok_flag and status != "OK":
        raise ApiError(ErrorCode.INTERNAL, f"Doris 导入失败: {msg}")
    return StreamLoadResult(status=status, loaded_rows=loaded, total_rows=total, message=msg, label=label)


def csv_row(values: list) -> str:
    """把一个值列表转成 CSV 行（含转义）。用于 Stream Load 数据组装。"""
    import csv as _csv

    buf = io.StringIO()
    _csv.writer(buf, lineterminator="\n").writerow(values)
    return buf.getvalue()


def make_label(job_id: str, attempt: int) -> str:
    """生成幂等 Stream Load label（label 全局唯一）。"""
    ts = str(time.time()).replace(".", "")
    return f"dataplat_{job_id}_{attempt}_{ts}"[:64]