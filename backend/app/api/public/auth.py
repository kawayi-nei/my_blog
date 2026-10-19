from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.api.deps import COOKIE_NAME, get_current_user
from app.core.config import get_settings
from app.core.security import (
    DUMMY_PASSWORD_HASH,
    create_access_token,
    verify_password,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import LoginRequest, LoginResponse, MeResponse
from app.services.rate_limit import login_limiter

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
async def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
) -> LoginResponse:
    settings = get_settings()
    if not settings.admin_enabled:
        raise HTTPException(status_code=404)

    client_ip = request.client.host if request.client else "unknown"
    if not login_limiter.try_acquire(client_ip):
        raise HTTPException(status_code=429, detail="尝试次数过多，请稍后再试")

    result = await db.execute(select(User).where(User.username == payload.username))
    user = result.scalar_one_or_none()
    password_hash = user.password_hash if user is not None else DUMMY_PASSWORD_HASH
    valid = await run_in_threadpool(verify_password, payload.password, password_hash)
    if user is None or not valid:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    login_limiter.reset(client_ip)
    token = create_access_token(user.id)
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=settings.jwt_expire_days * 24 * 3600,
        path="/",
    )
    return LoginResponse(username=user.username)


@router.post("/logout", status_code=204)
async def logout(response: Response) -> None:
    settings = get_settings()
    if not settings.admin_enabled:
        raise HTTPException(status_code=404)
    response.delete_cookie(
        COOKIE_NAME,
        path="/",
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
    )


@router.get("/me", response_model=MeResponse)
async def me(user: User = Depends(get_current_user)) -> MeResponse:
    return MeResponse(username=user.username)
