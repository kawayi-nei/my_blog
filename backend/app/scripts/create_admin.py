import asyncio

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import hash_password
from app.db.session import SessionLocal, engine
from app.models.user import User


async def main() -> None:
    settings = get_settings()
    async with SessionLocal() as db:
        result = await db.execute(
            select(User).where(User.username == settings.admin_username)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                username=settings.admin_username,
                password_hash=hash_password(settings.admin_password),
            )
            db.add(user)
            print(f"created admin: {settings.admin_username}")
        else:
            user.password_hash = hash_password(settings.admin_password)
            print(f"updated admin password: {settings.admin_username}")
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
