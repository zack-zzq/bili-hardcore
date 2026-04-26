"""认证相关路由"""

from fastapi import APIRouter, Depends, HTTPException, status

from bili_hardcore.auth import create_access_token, get_current_user, verify_credentials
from bili_hardcore.models import LoginRequest, TokenResponse

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    """用户名密码登录，返回 JWT"""
    if not verify_credentials(req.username, req.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    token = create_access_token(req.username)
    return TokenResponse(access_token=token)


@router.get("/verify")
async def verify(username: str = Depends(get_current_user)):
    """验证 token 有效性"""
    return {"username": username}
