"""JWT 签发 / 校验与账号验证（P0 环境变量单账号）。"""

import hmac
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import Request

from app.core.config import settings
from app.core.exceptions import ApiError, ErrorCode


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> Optional[str]:
    """解码并返回 subject；无效 / 过期返回 None（不暴露失败细节）。"""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except jwt.InvalidTokenError:
        return None
    sub = payload.get("sub")
    return sub if isinstance(sub, str) and sub else None


def get_current_user(request: Request) -> str:
    """从 Authorization: Bearer <token> 解析当前用户；失败抛 40100。"""
    auth = request.headers.get("Authorization", "")
    scheme, _, token = auth.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise ApiError(ErrorCode.UNAUTHORIZED, "未认证或登录已过期", status_code=401)
    username = decode_token(token)
    if username is None:
        raise ApiError(ErrorCode.UNAUTHORIZED, "未认证或登录已过期", status_code=401)
    return username


def verify_admin(username: str, password: str) -> bool:
    """环境变量单账号校验（常量时间比较，防时序攻击）。"""
    user_ok = hmac.compare_digest(username.encode(), settings.admin_user.encode())
    pass_ok = hmac.compare_digest(password.encode(), settings.admin_password.encode())
    return user_ok and pass_ok
