"""类型映射 / DDL 生成 单元测试。"""

import pytest

from app.modules.datasource.sync.common import (
    InferredColumn,
    doris_ddl,
    infer_xlsx_columns,
    maxcompute_to_doris,
    mysql_to_doris,
)


@pytest.mark.parametrize(
    ("src", "expect"),
    [
        ("int", "INT"),
        ("INT UNSIGNED", "INT"),
        ("bigint", "BIGINT"),
        ("smallint", "SMALLINT"),
        ("tinyint", "TINYINT"),
        ("float", "FLOAT"),
        ("double", "DOUBLE"),
        ("decimal(20,2)", "DECIMAL(20,2)"),
        ("numeric", "DECIMAL"),
        ("date", "DATEV2"),
        ("datetime", "DATETIME"),
        ("timestamp", "DATETIME"),
        ("varchar(64)", "VARCHAR(64)"),
        ("char(4)", "CHAR(4)"),
        ("text", "VARCHAR(65533)"),
        ("longtext", "VARCHAR(65533)"),
        ("blob", "VARCHAR(65533)"),
        ("json", "VARCHAR(65533)"),
        ("tinyint(1)", "TINYINT"),
        ("bool", "BOOLEAN"),
        ("unknown_type", "VARCHAR(65533)"),
    ],
)
def test_mysql_to_doris(src, expect):
    assert mysql_to_doris(src) == expect


@pytest.mark.parametrize(
    ("src", "expect"),
    [
        ("string", "VARCHAR(65533)"),
        ("varchar(32)", "VARCHAR(32)"),
        ("char(2)", "CHAR(2)"),
        ("bigint", "BIGINT"),
        ("smallint", "SMALLINT"),
        ("int", "INT"),
        ("double", "DOUBLE"),
        ("float", "FLOAT"),
        ("decimal(18,0)", "DECIMAL(18,0)"),
        ("boolean", "BOOLEAN"),
        ("datetime", "DATETIME"),
        ("timestamp", "DATETIME"),
        ("date", "DATEV2"),
        ("array", "VARCHAR(65533)"),
        ("map", "VARCHAR(65533)"),
        ("struct", "VARCHAR(65533)"),
    ],
)
def test_maxcompute_to_doris(src, expect):
    assert maxcompute_to_doris(src) == expect


def test_infer_xlsx_columns_types():
    header = ["id", "amount", "flag", "name", "empty"]
    sample = [[1, 2.5, True, "x", None], [3, 4.0, False, "yy", None]]
    cols = infer_xlsx_columns(header, sample)
    by_name = {c.name: c.doris_type for c in cols}
    assert by_name["id"] == "BIGINT"
    assert by_name["amount"] == "DOUBLE"
    assert by_name["flag"] == "BOOLEAN"
    assert by_name["name"] == "VARCHAR(65533)"
    assert by_name["empty"] == "VARCHAR(65533)"  # 全空列回退 VARCHAR


def test_infer_xlsx_float_with_mixed_sampled_regression():
    # 样例全为可转 float（int 也算）→ DOUBLE；含字符串 → VARCHAR
    assert infer_xlsx_columns(["n"], [[1], [2.0]])[0].doris_type == "DOUBLE"
    assert infer_xlsx_columns(["n"], [[1], ["2"]])[0].doris_type == "VARCHAR(65533)"


def test_doris_ddl_generates():
    cols = [InferredColumn("id", "BIGINT"), InferredColumn("name", "VARCHAR(64)")]
    ddl = doris_ddl("credit", "ods_orders", cols)
    assert "CREATE TABLE IF NOT EXISTS `credit`.`ods_orders`" in ddl
    assert "`id` BIGINT" in ddl
    assert "UNIQUE KEY (`id`)" in ddl
    assert "DISTRIBUTED BY HASH (`id`) BUCKETS 8" in ddl
    assert 'replication_num' in ddl


def test_doris_ddl_requires_column():
    with pytest.raises(Exception):
        doris_ddl("credit", "t", [])