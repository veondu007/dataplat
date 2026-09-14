from fastapi import APIRouter, Request

from app.core.config import settings
from app.core.exceptions import ApiError, ErrorCode
from app.core.response import ok
from app.core.security import create_access_token, get_current_user, verify_admin
from app.modules.auth.schemas import LoginRequest

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login")
def login(body: LoginRequest):
    if not verify_admin(body.username, body.password):
        raise ApiError(ErrorCode.UNAUTHORIZED, "用户名或密码错误", status_code=401)
    token = create_access_token(body.username)
    return ok(
        {
            "token": token,
            "expires_in": settings.jwt_expire_minutes * 60,
            "user": {"username": body.username},
        }
    )


@router.get("/me")
def me(request: Request):
    username = get_current_user(request)
    return ok({"username": username})
