"""Doris 元数据采集器单元测试：mock pymysql,不依赖真实 Doris。"""

import pytest

from app.modules.asset.collector import (
    DorisMetadataConnector,
    _extract_partition_keys,
    _to_int,
)


class _FakeConn:
    """模拟 pymysql 连接,按 SQL 片段返回预设行。"""

    def __init__(self, plan):
        self.plan = plan  # {sql_substring: rows}
        self.closed = False

    def cursor(self):
        return _FakeCursor(self.plan)

    def close(self):
        self.closed = True


class _FakeCursor:
    def __init__(self, plan):
        self.plan = plan
        self.last_sql = ""

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, sql, args=None):
        self.last_sql = sql
        return 0

    def fetchall(self):
        for key, rows in self.plan.items():
            if key.lower() in self.last_sql.lower():
                return rows
        return []

    def fetchone(self):
        rows = self.fetchall()
        return rows[0] if rows else None


@pytest.fixture
def conn_factory(monkeypatch):
    def make(plan):
        conn = _FakeConn(plan)

        def fake_connect(self):
            return conn

        monkeypatch.setattr(DorisMetadataConnector, "_connect", fake_connect)
        return conn

    return make


def test_to_int():
    assert _to_int(100) == 100
    assert _to_int("0") == 0
    assert _to_int(None) is None
    assert _to_int("") == 0


def test_extract_partition_keys():
    assert _extract_partition_keys("PARTITION BY RANGE(`dt`)...") == {"dt"}
    assert _extract_partition_keys("PARTITION BY RANGE COLUMNS(a, b)") == {"a", "b"}
    assert _extract_partition_keys("PARTITION BY LIST(code)") == {"code"}
    assert _extract_partition_keys("UNIQUE KEY(id) DISTRIBUTED BY HASH(id)") == set()


def test_list_databases_filters_system(conn_factory):
    c = DorisMetadataConnector("h", 9030, "u", "p")
    conn = conn_factory(
        {
            "SELECT SCHEMA_NAME": [
                ("__internal_schema",),
                ("information_schema",),
                ("credit",),
                ("business",),
            ]
        }
    )
    assert c.list_databases() == ["business", "credit"]
    assert conn.closed


def test_list_tables_parses_stats(conn_factory):
    from datetime import datetime

    c = DorisMetadataConnector("h", 9030, "u", "p")
    conn = conn_factory(
        {
            "SELECT TABLE_NAME": [
                (
                    "customer",
                    "客户表",
                    "UNIQUE",
                    100,
                    2048,
                    datetime(2026, 1, 1, 0, 0, 0),
                    datetime(2026, 1, 2, 0, 0, 0),
                )
            ]
        }
    )
    tables = c.list_tables("credit")
    assert tables[0]["name"] == "customer"
    assert tables[0]["comment"] == "客户表"
    assert tables[0]["engine"] == "UNIQUE"
    assert tables[0]["num_rows"] == 100
    assert tables[0]["data_size"] == 2048
    assert str(tables[0]["update_time"]) == "2026-01-02 00:00:00"
    assert conn.closed


def test_list_columns_marks_partition(conn_factory, monkeypatch):
    c = DorisMetadataConnector("h", 9030, "u", "p")
    _conn = conn_factory(
        {
            "SELECT COLUMN_NAME": [
                ("id", "BIGINT", 1, "", "NO", None),
                ("dt", "DATEV2", 2, "分区", "YES", None),
                ("name", "VARCHAR", 3, "", "YES", 64),
            ]
        }
    )
    monkeypatch.setattr(c, "_partition_keys", lambda db, t: {"dt"})
    cols = c.list_columns("credit", "customer")
    by_name = {c_["name"]: c_ for c_ in cols}
    assert by_name["id"]["data_type"] == "BIGINT"
    assert by_name["name"]["data_type"] == "VARCHAR(64)"
    assert by_name["dt"]["is_partition"] is True
    assert by_name["id"]["is_partition"] is False


def test_partition_keys_uses_show_create(conn_factory, monkeypatch):
    c = DorisMetadataConnector("h", 9030, "u", "p")
    conn = conn_factory(
        {
            "SHOW CREATE": [("CREATE TABLE t (x INT) PARTITION BY RANGE(`dt`) ...",)]
        }
    )
    keys = c._partition_keys("credit", "customer")
    assert keys == {"dt"}
    assert conn.closed