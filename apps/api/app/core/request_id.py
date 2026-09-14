"""请求级 request_id（contextvars 实现，无外部依赖）。

一个 HTTP 请求共享同一个 request_id：中间件生成并写入 contextvar，
``ok()`` / ``fail()`` / 异常处理器在同一请求的 task 内均可读取。
"""

import uuid
from contextvars import ContextVar

_request_id: ContextVar[str] = ContextVar("request_id", default="")


def new_request_id() -> str:
    return uuid.uuid4().hex


def set_request_id(rid: str) -> None:
    _request_id.set(rid)


def current_request_id() -> str:
    return _request_id.get() or new_request_id()
