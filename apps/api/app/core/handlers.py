from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.exceptions import ApiError, ErrorCode
from app.core.response import fail


def register_exception_handlers(app: FastAPI) -> None:
    """把业务异常、参数校验失败、HTTPException 统一收编为响应信封。"""

    @app.exception_handler(ApiError)
    async def _handle_api_error(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(exc.code, exc.message),
        )

    @app.exception_handler(RequestValidationError)
    async def _handle_validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        errors = exc.errors()
        detail = "; ".join(
            f"{'.'.join(str(p) for p in e.get('loc', ()))}: {e.get('msg', '')}" for e in errors
        )
        return JSONResponse(
            status_code=422,
            content=fail(ErrorCode.VALIDATION, detail or "参数校验失败"),
        )

    @app.exception_handler(StarletteHTTPException)
    async def _handle_http_exception(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content=fail(ErrorCode.NOT_FOUND if exc.status_code == 404 else ErrorCode.INTERNAL, str(exc.detail)),
        )

