import pytest

from app.core.exceptions import SqlGuardError
from app.modules.sql.guard import assert_readonly


@pytest.mark.parametrize(
    "sql",
    [
        "SELECT 1",
        "SELECT * FROM orders LIMIT 10",
        "WITH x AS (SELECT 1) SELECT * FROM x",
        "EXPLAIN SELECT * FROM orders",
        "DESC orders",
        "DESCRIBE orders",
        "SHOW TABLES",
        "SELECT 'drop table x'",  # 字符串里的写关键字不拦
        "SELECT 1 -- drop table x",  # 行注释里的写关键字不拦
        "SELECT /* drop */ 1",  # 块注释里的写关键字不拦
    ],
)
def test_readonly_allowed(sql: str):
    assert_readonly(sql)


@pytest.mark.parametrize(
    "sql",
    [
        "DROP TABLE orders",
        "DELETE FROM orders WHERE id = 1",
        "INSERT INTO orders VALUES (1)",
        "UPDATE orders SET amount = 0",
        "TRUNCATE TABLE orders",
        "ALTER TABLE orders ADD COLUMN x INT",
        "CREATE TABLE t (id INT)",
        "SELECT 1; DROP TABLE orders",  # 多语句混合
        "EXPLAIN INSERT INTO orders VALUES (1)",  # EXPLAIN 内部写操作
        "SELECT 1 FOR UPDATE",  # 带写锁
        "not sql at all",  # 无法解析
        "",
        "   ",
        "-- only a comment",
    ],
)
def test_write_or_invalid_rejected(sql: str):
    with pytest.raises(SqlGuardError) as exc:
        assert_readonly(sql)
    assert "SELECT" in str(exc.value.message) or "不能为空" in str(exc.value.message)


def test_empty_rejected_with_specific_message():
    with pytest.raises(SqlGuardError) as exc:
        assert_readonly("")
    assert "不能为空" in str(exc.value.message)
