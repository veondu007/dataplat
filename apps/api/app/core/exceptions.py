"""平台级异常与业务错误码。

统一响应信封：``{code, message, data, request_id}``。
错误码约定：``0`` 成功；``4xxxx`` 业务可预期错误；``5xxxx`` 服务端错误。
详见 ``docs/04-api/API设计规范.md``。
"""


class ErrorCode:
    OK = 0
    VALIDATION = 40000  # 参数校验失败（HTTP 422）
    SQL_GUARD = 40001  # SQL 护栏拦截
    UNAUTHORIZED = 40100  # 未认证（预留）
    FORBIDDEN = 40300  # 无权限（预留）
    NOT_FOUND = 40400  # 资源不存在（预留）
    INTERNAL = 50000  # 服务端内部错误


class ApiError(Exception):
    """业务异常：由全局异常处理器转成统一响应信封。"""

    def __init__(self, code: int, message: str, status_code: int = 400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code


class SqlGuardError(ApiError):
    """SQL 护栏拦截：仅允许 SELECT / SHOW / EXPLAIN / DESC。"""

    def __init__(self, message: str):
        super().__init__(code=ErrorCode.SQL_GUARD, message=message, status_code=400)
