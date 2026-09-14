import re

_WRITE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|load|grant|revoke)\b",
    re.IGNORECASE,
)


def assert_readonly(sql: str) -> None:
    if not sql or not sql.strip():
        raise ValueError("SQL 不能为空")
    if _WRITE.search(sql):
        raise ValueError("临时查询与问数仅允许 SELECT / SHOW / EXPLAIN / DESC")
