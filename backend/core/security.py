from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional
from ..modules.auth_service import auth_service, decode_token
from ..schemas.auth import TokenData

security = HTTPBearer()


async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
) -> TokenData:
    token = credentials.credentials

    payload = decode_token(token)
    if payload is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的认证凭证",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return TokenData(
        user_id=payload.get("sub"),
        username=payload.get("username"),
        role=payload.get("role"),
    )


def require_teacher(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != "teacher":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要教师权限"
        )
    return current_user


def require_student(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role != "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="需要学生权限"
        )
    return current_user


def require_any_role(current_user: TokenData = Depends(get_current_user)) -> TokenData:
    if current_user.role not in ["teacher", "student"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="权限不足")
    return current_user
