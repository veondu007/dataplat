"""数据源护栏单元测试。"""

import pytest

from app.core.exceptions import ApiError
from app.modules.datasource.guard import assert_target_database, assert_target_table, assert_valid_engine


@pytest.mark.parametrize(
    "engine",
    ["mysql", "maxcompute", "xlsx"],
)
def test_valid_engine(engine):
    assert assert_valid_engine(engine) == engine


@pytest.mark.parametrize("engine", ["doris", "hive", "", "MySQL", "spark"])
def test_invalid_engine(engine):
    with pytest.raises(ApiError) as exc:
        assert_valid_engine(engine)
    assert exc.value.code == 40000


@pytest.mark.parametrize(
    "table",
    ["orders", "ods_orders", "_meta", "a1_b2", "x" * 64],
)
def test_valid_target_table(table):
    assert assert_target_table(table) == table


@pytest.mark.parametrize(
    "table",
    ["orders;drop", "my-table", "1abc", "orders table", "a.b", "", None, "select *"],
)
def test_invalid_target_table(table):
    with pytest.raises(ApiError):
        assert_target_table(table)  # type: ignore[arg-type]


def test_target_database_validation():
    assert assert_target_database("credit") == "credit"
    with pytest.raises(ApiError):
        assert_target_database("credit;drop database x")
    with pytest.raises(ApiError):
        assert_target_database("")