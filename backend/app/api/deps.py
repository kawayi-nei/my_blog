from fastapi import Depends, HTTPException, Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import decode_access_token
from app.db.session import get_db
from app.models.user import User

COOKIE_NAME = "access_token"


async def get_current_user(
    request: Request, db: AsyncSession = Depends(get_db)
) -> User:
    if not get_settings().admin_enabled:
        raise HTTPException(status_code=401, detail="未登录")
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
