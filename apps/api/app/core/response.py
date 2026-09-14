from typing import Any
from uuid import uuid4


def ok(data: Any = None, message: str = "ok") -> dict:
    return {
        "code": 0,
        "message": message,
        "data": data,
        "request_id": str(uuid4()),
    }
