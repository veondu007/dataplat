from typing import Any

from app.core.request_id import current_request_id


def ok(data: Any = None, message: str = "ok") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": current_request_id(),
    }


def fail(code: int, message: str, data: Any = None) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data,
        "request_id": current_request_id(),
    }
