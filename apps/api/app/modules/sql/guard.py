"""SQL 只读护栏：关键字扫描 + sqlglot AST 双层拦截。

策略（fail-closed）：
1. 去注释 / 去字符串后扫描写关键字，命中即拒（防绕过、防误报）。
2. ``sqlglot.parse(sql, read="doris")`` 解析，任一语句失败 / 无法识别即整体拒绝；
   仅允许 ``Select`` / ``Show`` / ``Describe``（EXPLAIN / DESC / DESCRIBE）。
3. ``EXPLAIN`` 的 inner 语句必须同样只读（防 ``EXPLAIN INSERT ...``）。

已知限制：生僻的 Doris ``SHOW`` 变体可能被解析为 ``Command`` 而误拒（fail-closed，可接受）；
``SELECT ... FOR UPDATE`` 暂放行。
"""

import re
from typing import Iterable

from sqlglot import exp, parse

from app.core.exceptions import SqlGuardError

_READONLY_MSG = "临时查询与问数仅允许 SELECT / SHOW / EXPLAIN / DESC"

_WRITE = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|load|grant|revoke|"
    r"merge|replace|rename|set)\b",
    re.IGNORECASE,
)

# 允许的顶层语句类型（Describe 涵盖 EXPLAIN / DESC / DESCRIBE；WITH 折进 Select）
_ALLOWED = (exp.Select, exp.Show, exp.Describe)

# sqlglot 对无法解析的语句在 parse() 里返回 None 元素而不是抛异常；
# 但部分明显残缺 SQL 会直接抛 ParseError，需一并 catch。
_parse = parse  # type: ignore[assignment]


def assert_readonly(sql: str) -> None:
    """校验 SQL 只读；违规抛出 :class:`SqlGuardError`。"""
    if not sql or not sql.strip():
        raise SqlGuardError("SQL 不能为空")

    stripped = strip_comments_and_strings(sql)
    if _WRITE.search(stripped):
        raise SqlGuardError(_READONLY_MSG)

    statements = _parse_sql(sql)
    if not statements:
        raise SqlGuardError(_READONLY_MSG)

    for stmt in statements:
        _assert_statement_readonly(stmt)

    # Select 带锁（FOR UPDATE / LOCK IN SHARE MODE）会加写锁，禁止
    for stmt in statements:
        if isinstance(stmt, exp.Select) and stmt.args.get("locks"):
            raise SqlGuardError(_READONLY_MSG)


def strip_comments_and_strings(sql: str) -> str:
    """去掉注释与字符串字面量，供关键字扫描使用（防绕过 / 防误报）。"""
    out: list[str] = []
    i, n = 0, len(sql)
    while i < n:
        ch = sql[i]
        nxt = sql[i + 1] if i + 1 < n else ""
        if ch == "-" and nxt == "-":
            # 行注释：-- ... EOL
            i += 2
            while i < n and sql[i] != "\n":
                i += 1
            out.append(" ")
            continue
        if ch == "#":
            # MySQL/Doris 行注释：#
            i += 1
            while i < n and sql[i] != "\n":
                i += 1
            out.append(" ")
            continue
        if ch == "/" and nxt == "*":
            # 块注释：/* ... */（含嵌套）
            depth = 1
            i += 2
            while i < n and depth:
                if sql[i] == "/" and i + 1 < n and sql[i + 1] == "*":
                    depth += 1
                    i += 2
                elif sql[i] == "*" and i + 1 < n and sql[i + 1] == "/":
                    depth -= 1
                    i += 2
                else:
                    i += 1
            out.append(" ")
            continue
        if ch in ("'", '"', "`"):
            # 字符串 / 反引号标识符（含反斜杠转义）
            i = _skip_quoted(sql, i, ch)
            out.append(" ")
            continue
        out.append(ch)
        i += 1
    return "".join(out)


def _skip_quoted(sql: str, start: int, quote: str) -> int:
    i = start + 1
    n = len(sql)
    while i < n:
        if sql[i] == "\\":
            i += 2
            continue
        if sql[i] == quote:
            return i + 1
        i += 1
    return n


def _parse_sql(sql: str):
    try:
        return _parse(sql, read="doris")
    except Exception:
        # Doris 方言异常时回退 MySQL（同为 MySQL 协议）
        try:
            return _parse(sql, read="mysql")
        except Exception as exc:
            raise SqlGuardError(_READONLY_MSG) from exc


def _assert_statement_readonly(stmt: "exp.Expression") -> None:
    if stmt is None:
        raise SqlGuardError(_READONLY_MSG)
    if isinstance(stmt, exp.Describe):
        # EXPLAIN / DESC：inner 若是语句（如 EXPLAIN INSERT ...）必须同样只读；
        # inner 若是 Table（DESC t）则天然安全，不再递归
        inner = stmt.args.get("this")
        if isinstance(inner, exp.Expression) and not isinstance(inner, exp.Table):
            _assert_statement_readonly(inner)
        return
    if not isinstance(stmt, _ALLOWED):
        raise SqlGuardError(_READONLY_MSG)


def _iter_statements(stmts: Iterable) -> None:
    """保留给未来扩展使用（当前直接遍历 parse 结果）。"""
    for s in stmts:
        _assert_statement_readonly(s)
