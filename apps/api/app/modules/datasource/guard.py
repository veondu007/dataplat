"""数据源模块护栏：引擎白名单 + 目标表名校验（防注入）。"""

from __future__ import annotations

import re

from app.core.exceptions import ApiError, ErrorCode

VALID_ENGINES = ("mysql", "maxcompute", "xlsx")

# Doris 标识符：字母/数字/下划线开头字母或下划线
_TABLE_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def assert_valid_engine(engine: str) -> str:
    if engine not in VALID_ENGINES:
        raise ApiError(
            ErrorCode.VALIDATION,
            f"不支持的引擎类型: {engine}（仅支持 {', '.join(VALID_ENGINES)}）",
            status_code=400,
        )
    return engine


def assert_target_table(table: str) -> str:
    if not table or not _TABLE_RE.match(table):
        raise ApiError(
            ErrorCode.VALIDATION,
            f"非法目标表名: {table!r}（仅允许字母/数字/下划线，且不能以下划线开头之外的非法字符）",
            status_code=400,
        )
    return table


def assert_target_database(db: str) -> str:
    if not db or not _TABLE_RE.match(db):
        raise ApiError(ErrorCode.VALIDATION, f"非法目标库名: {db!r}", status_code=400)
    return db