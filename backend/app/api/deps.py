from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

COOKIE_NAME = "access_token"
UNSAFE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}


async def _get_user_or_401(request: Request, db: AsyncSession) -> User:
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="未登录")
    user_id = decode_access_token(token)
    if user_id is None:
        raise HTTPException(status_code=401, detail="登录已过期")
    user = await db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="用户不存在")
    return user


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    if not get_settings().admin_enabled:
        raise HTTPException(status_code=401, detail="未登录")
    return await _get_user_or_401(request, db)


async def require_admin(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    if not get_settings().admin_enabled:
        raise HTTPException(status_code=404)
    return await _get_user_or_401(request, db)


async def require_same_origin(request: Request) -> None:
    if request.method not in UNSAFE_METHODS:
        return
    origin = request.headers.get("origin")
    expected = get_settings().site_origin.rstrip("/")
    if not origin or origin.rstrip("/") != expected:
        raise HTTPException(status_code=403, detail="来源校验失败")
