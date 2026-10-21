import asyncio
import os
import subprocess
import sys
from pathlib import Path

import asyncpg
import pytest
import pytest_asyncio
from dotenv import load_dotenv

env_test = Path(__file__).resolve().parents[1] / ".env.test"
if not env_test.exists():
    raise RuntimeError("backend/.env.test is required for tests")

load_dotenv(env_test, override=True)

from httpx import ASGITransport, AsyncClient  # noqa: E402
from sqlalchemy.ext.asyncio import (  # noqa: E402
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool  # noqa: E402

from app import models  # noqa: E402,F401
from app.core.config import get_settings  # noqa: E402
from app.db.base import Base  # noqa: E402
from app.db.session import get_db  # noqa: E402
from app.main import app  # noqa: E402

get_settings.cache_clear()
settings = get_settings()
if not settings.database_url.endswith("/my_blog_test"):
    raise RuntimeError("Tests must use the my_blog_test database")
engine = create_async_engine(settings.database_url, poolclass=NullPool)
TestingSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session", autouse=True)
def run_migration_smoke():
    backend_dir = Path(__file__).resolve().parents[1]
    url = settings.database_url.replace("postgresql+asyncpg://", "postgresql://")

    async def drop_all():
        conn = await asyncpg.connect(url)
        await conn.execute(
            "DROP TABLE IF EXISTS projects, media, post_tags, posts, tags, users, alembic_version CASCADE"
        )
        await conn.close()

    async def inspect():
        conn = await asyncpg.connect(url)
        tables = {
            row["tablename"]
            for row in await conn.fetch(
                "select tablename from pg_tables where schemaname='public'"
            )
        }
        constraints = {
            row["conname"]
            for row in await conn.fetch(
                """
                select conname
                from pg_constraint
                where conrelid = 'posts'::regclass and contype = 'c'
                """
            )
        }
        indexes = {
            row["indexname"]
            for row in await conn.fetch(
                """
                select indexname
                from pg_indexes
                where schemaname='public' and tablename='posts'
                """
            )
        }
        project_constraints = {
            row["conname"]
            for row in await conn.fetch(
                """
                select conname
                from pg_constraint
                where conrelid = 'projects'::regclass and contype = 'c'
                """
            )
        }
        project_indexes = {
            row["indexname"]
            for row in await conn.fetch(
                """
                select indexname
                from pg_indexes
                where schemaname='public' and tablename='projects'
                """
            )
        }
        await conn.close()
        return (
            tables,
            constraints,
            indexes,
            project_constraints,
            project_indexes,
        )

    asyncio.run(drop_all())
    env = os.environ.copy()
    env["DATABASE_URL"] = settings.database_url
    subprocess.run(
        [sys.executable, "-m", "alembic", "upgrade", "head"],
        cwd=backend_dir,
        env=env,
        check=True,
    )
    (
        tables,
        constraints,
        indexes,
        project_constraints,
        project_indexes,
    ) = asyncio.run(inspect())
    assert {
        "users",
        "posts",
        "tags",
        "post_tags",
        "media",
        "projects",
        "alembic_version",
    } <= tables
    assert {
        "ck_posts_language",
        "ck_posts_status",
        "ck_posts_slug_format",
    } <= constraints
    assert {
        "ix_posts_status_published_at",
        "ix_posts_title_trgm",
        "ix_posts_excerpt_trgm",
        "ix_posts_content_trgm",
    } <= indexes
    assert {"ck_projects_status", "ck_projects_slug_format"} <= project_constraints
    assert "ix_projects_public_order" in project_indexes
    asyncio.run(drop_all())


@pytest_asyncio.fixture(autouse=True)
async def setup_database():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield


@pytest_asyncio.fixture
async def db_session():
    async with TestingSessionLocal() as session:
        yield session


@pytest_asyncio.fixture
async def client(db_session):
    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
    app.dependency_overrides.pop(get_db, None)


@pytest_asyncio.fixture
async def admin_user(db_session):
    from app.core.security import hash_password
    from app.models.user import User

    user = User(
        username=settings.admin_username,
        password_hash=hash_password(settings.admin_password),
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)
    return user


@pytest.fixture
def origin_headers():
    return {"origin": get_settings().site_origin}


@pytest_asyncio.fixture
async def logged_in_client(client, admin_user):
    response = await client.post(
        "/api/auth/login",
        json={
            "username": get_settings().admin_username,
            "password": get_settings().admin_password,
        },
    )
    assert response.status_code == 200
    return client


@pytest_asyncio.fixture
async def admin_client(logged_in_client, origin_headers):
    logged_in_client.headers.update(origin_headers)
    return logged_in_client


@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path
