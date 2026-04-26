"""身份认证模块 - JWT 令牌生成与验证"""

from __future__ import annotations

import hashlib
import hmac
from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from bili_hardcore.config import (
    AUTH_PASSWORD,
    AUTH_USERNAME,
    JWT_ALGORITHM,
    JWT_EXPIRE_HOURS,
    JWT_SECRET,
)

security = HTTPBearer(auto_error=False)


def _constant_time_compare(a: str, b: str) -> bool:
    """常量时间字符串比较，防止时序攻击"""
    return hmac.compare_digest(a.encode(), b.encode())


def verify_credentials(username: str, password: str) -> bool:
    """验证用户名和密码"""
    if not _constant_time_compare(username, AUTH_USERNAME):
        return False
    return _constant_time_compare(password, AUTH_PASSWORD)


def create_access_token(username: str) -> str:
    """创建 JWT 令牌"""
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRE_HOURS)
    payload = {"sub": username, "exp": expire}
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_token(token: str) -> str | None:
    """验证 JWT 令牌, 返回用户名或 None"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(security),
) -> str:
    """FastAPI 依赖项 — 从 Authorization header 提取并验证 token"""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="未提供认证信息",
        )
    username = verify_token(credentials.credentials)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="认证信息无效或已过期",
        )
    return username
