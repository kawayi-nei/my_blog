# 个人博客基础闭环 实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 打通 FastAPI + PostgreSQL + Next.js 的最小可运行闭环：健康检查、管理员登录开关、文章只读 API、深色双语站点壳、文章列表与详情。

**架构：** FastAPI 是唯一业务 API，Next.js 只负责 SSR 页面与国际化。开发时 Next rewrites 把 `/api` 与 `/uploads` 代理到 FastAPI；生产由 nginx 分流。本计划是 4 个计划中的第 1 个。

**技术栈：** Next.js 16.4.2（App Router）、TypeScript、Tailwind CSS v4、next-intl 4、FastAPI、SQLAlchemy 2 async、asyncpg、Alembic、PostgreSQL 17、pytest、Playwright。

---

## 范围与后续计划

本计划只覆盖规格中的第 13 节 M1–M3：

- M1 后端骨架、数据库迁移、健康检查
- M2 管理员种子、登录/登出/me、`ADMIN_ENABLED` 开关
- M3 文章只读 API + Next 脚手架 + 深色双语壳 + 首页/文章页

后续计划（不在本文件范围内）：

- 计划 2：后台文章 CRUD、Markdown 编辑器、图片上传
- 计划 3：作品集、标签搜索、评论、阅读统计
- 计划 4：双语完善、SEO、测试补齐、nginx + systemd 部署

## 文件结构

```
my_blog/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── core/{__init__.py,config.py,security.py}
│   │   ├── db/{__init__.py,base.py,session.py}
│   │   ├── models/{__init__.py,user.py,post.py,tag.py}
│   │   ├── schemas/{__init__.py,auth.py,site.py,post.py}
│   │   ├── api/
│   │   │   ├── __init__.py
│   │   │   ├── deps.py
│   │   │   ├── public/{__init__.py,auth.py,site.py,posts.py,tags.py}
│   │   │   └── admin/__init__.py
│   │   ├── services/{__init__.py,rate_limit.py,posts.py}
│   │   └── scripts/{__init__.py,create_admin.py,seed_demo.py}
│   ├── alembic/{env.py,script.py.mako,versions/0001_initial.py}
│   ├── tests/{conftest.py,test_health.py,test_auth.py,test_posts.py}
│   ├── alembic.ini
│   ├── pytest.ini
│   ├── requirements.txt
│   ├── .env.example
│   └── .env.test.example
├── frontend/
│   ├── src/
│   │   ├── app/[locale]/{layout.tsx,page.tsx,posts/page.tsx,posts/[slug]/page.tsx}
│   │   ├── app/globals.css
│   │   ├── components/{site-header.tsx,site-footer.tsx,post-card.tsx,markdown.tsx}
│   │   ├── content/site.ts
│   │   ├── i18n/{routing.ts,request.ts,navigation.ts}
│   │   ├── lib/api.ts
│   │   ├── messages/{zh.json,en.json}
│   │   └── proxy.ts
│   ├── e2e/{global-setup.ts,public.spec.ts}
│   ├── playwright.config.ts
│   ├── next.config.ts
│   ├── .env.local.example
│   └── package.json
└── README.md
```

---

### 任务 1：创建 Next.js 项目并安装前端依赖

**文件：**
- 创建：`frontend/`（由 create-next-app 生成）
- 修改：`frontend/package.json`

- [ ] **步骤 1：生成 Next.js 项目**

```bash
cd "Z:/my_blog"
npx create-next-app@latest frontend --ts --tailwind --eslint --app --src-dir --import-alias "@/*" --use-npm --empty --disable-git --yes
```

解释：在空目录 `frontend/` 生成 Next.js 16 + TypeScript + Tailwind + App Router 项目；`--disable-git` 避免在父仓库里再建一个 git 仓库。

预期：命令结束无报错，`frontend/package.json` 存在。

- [ ] **步骤 2：安装依赖**

```bash
cd "Z:/my_blog/frontend"
npm install next-intl react-markdown remark-gfm rehype-highlight highlight.js @tailwindcss/typography
npm install -D @playwright/test
npx playwright install chromium
```

解释：
- `next-intl`：中英文界面
- `react-markdown` + `remark-gfm` + `rehype-highlight` + `highlight.js`：Markdown 与代码高亮
- `@tailwindcss/typography`：正文排版
- `@playwright/test`：端到端测试，`install chromium` 下载测试浏览器

- [ ] **步骤 3：验证构建**

```bash
npm run build
```

预期：构建成功。若 Next 提示未使用的默认页面，后续任务会删除它们。

- [ ] **步骤 4：Commit**

```bash
cd "Z:/my_blog"
git add frontend
git commit -m "chore: scaffold Next.js frontend"
```

---

### 任务 2：后端配置与健康检查（TDD）

**文件：**
- 创建：`backend/app/__init__.py`
- 创建：`backend/app/core/__init__.py`
- 创建：`backend/app/core/config.py`
- 创建：`backend/app/db/__init__.py`
- 创建：`backend/app/db/base.py`
- 创建：`backend/app/db/session.py`
- 创建：`backend/app/main.py`
- 创建：`backend/.env.example`
- 创建：`backend/.env.test.example`
- 创建：`backend/pytest.ini`
- 创建：`backend/tests/conftest.py`
- 创建：`backend/tests/test_health.py`
- 创建：`backend/tests/test_config.py`
- 创建：`backend/requirements.txt`

- [ ] **步骤 1：创建测试数据库**

```bash
psql -U postgres -h 127.0.0.1 -d postgres -c "CREATE DATABASE my_blog_test OWNER blog_user;"
psql -U postgres -h 127.0.0.1 -d my_blog_test -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

解释：测试使用独立库 `my_blog_test`，避免清空开发数据；扩展与正式库保持一致。

- [ ] **步骤 2：写失败的测试**

创建 `backend/tests/conftest.py`：

```python
from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv

env_test = Path(__file__).resolve().parents[1] / ".env.test"
if not env_test.exists():
    raise RuntimeError(
        f"Missing {env_test}; copy .env.test.example and fill in credentials"
    )

load_dotenv(env_test, override=True)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
```

创建 `backend/tests/test_health.py`：

```python
async def test_health(client):
    response = await client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

创建 `backend/tests/test_config.py`：

```python
from app.core.config import get_settings


def test_tests_use_my_blog_test_database():
    assert get_settings().database_url.endswith("/my_blog_test")
```

创建 `backend/pytest.ini`：

```ini
[pytest]
asyncio_mode = auto
pythonpath = .
testpaths = tests
```

- [ ] **步骤 3：运行测试验证失败**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest tests/test_health.py -v
```

预期：FAIL 或收集错误。若 `.env.test` 还没创建，会提示 `RuntimeError: Missing .../.env.test`；否则提示 `ModuleNotFoundError: No module named 'app.main'`。

- [ ] **步骤 4：创建配置文件**

创建 `backend/app/core/config.py`：

```python
from functools import lru_cache
from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(BASE_DIR / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "My Blog API"
    database_url: str
    jwt_secret: str = Field(min_length=32)
    jwt_expire_days: int = 7
    admin_username: str = Field(default="admin", min_length=1, max_length=50)
    admin_password: str = Field(min_length=12)
    admin_enabled: bool = True
    upload_dir: str = str(BASE_DIR / "uploads")
    ip_hash_salt: str
    cookie_secure: bool = False
    site_origin: str = "http://localhost:3000"

    @field_validator("jwt_secret", "admin_password")
    @classmethod
    def reject_placeholders(cls, value: str) -> str:
        if value.startswith("replace-with"):
            raise ValueError("Replace placeholder secrets in .env")
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
```

创建 `backend/app/db/base.py`：

```python
from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    pass
```

创建 `backend/app/db/session.py`：

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings

settings = get_settings()
engine = create_async_engine(settings.database_url, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with SessionLocal() as session:
        yield session
```

创建 `backend/app/main.py`：

```python
from fastapi import FastAPI

from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

创建空的包文件：

```bash
cd "Z:/my_blog/backend"
mkdir -p app/core app/db app/models app/schemas app/api/public app/api/admin app/services app/scripts tests
touch app/__init__.py app/core/__init__.py app/db/__init__.py app/models/__init__.py app/schemas/__init__.py app/api/__init__.py app/api/public/__init__.py app/api/admin/__init__.py app/services/__init__.py app/scripts/__init__.py
```

- [ ] **步骤 5：创建环境文件**

创建 `backend/.env.example`：

```env
DATABASE_URL=postgresql+asyncpg://blog_user:YOUR_PASSWORD@127.0.0.1:5432/my_blog
JWT_SECRET=replace-with-a-long-random-string
JWT_EXPIRE_DAYS=7
ADMIN_USERNAME=admin
ADMIN_PASSWORD=replace-with-a-strong-password
ADMIN_ENABLED=true
# UPLOAD_DIR=
IP_HASH_SALT=replace-with-a-random-string
COOKIE_SECURE=false
SITE_ORIGIN=http://localhost:3000
```

创建 `backend/.env.test.example`：

```env
DATABASE_URL=postgresql+asyncpg://blog_user:YOUR_PASSWORD@127.0.0.1:5432/my_blog_test
JWT_SECRET=test-secret-0123456789abcdef0123456789abcdef
JWT_EXPIRE_DAYS=7
ADMIN_USERNAME=admin
ADMIN_PASSWORD=test-password
ADMIN_ENABLED=true
IP_HASH_SALT=test-salt
COOKIE_SECURE=false
SITE_ORIGIN=http://localhost:3000
```

复制并填写真实密码：

```bash
cd "Z:/my_blog/backend"
cp .env.example .env
cp .env.test.example .env.test
```

解释：把两个文件里的 `YOUR_PASSWORD` 换成你的 `blog_user` 密码；`.env` 用于开发，`.env.test` 用于测试。

- [ ] **步骤 6：运行测试验证通过**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest tests/test_health.py -v
```

预期：`2 passed`（健康检查 + 测试环境防呆）。

- [ ] **步骤 7：锁定依赖版本**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pip freeze > requirements.txt
```

解释：把当前 venv 的依赖版本写入 `requirements.txt`，方便以后在服务器复现。

- [ ] **步骤 8：Commit**

先把 `.env.test` 加入 `.gitignore`，再提交：

```bash
printf "\n.env.test\n" >> "Z:/my_blog/.gitignore"
cd "Z:/my_blog"
git add .gitignore backend/.env.example backend/.env.test.example backend/requirements.txt backend/pytest.ini backend/app backend/tests
git commit -m "feat: add backend config and health endpoint"
```

注意：不要提交 `.env` 和 `.env.test`。

---

### 任务 3：数据模型与 Alembic 初始迁移

**文件：**
- 创建：`backend/app/models/user.py`
- 创建：`backend/app/models/post.py`
- 创建：`backend/app/models/tag.py`
- 修改：`backend/app/models/__init__.py`
- 创建：`backend/alembic.ini`
- 创建：`backend/alembic/env.py`
- 创建：`backend/alembic/versions/0001_initial.py`
- 修改：`backend/tests/conftest.py`

- [ ] **步骤 1：初始化 Alembic（异步模板）**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m alembic init -t async alembic
```

解释：生成 `alembic.ini` 和 `alembic/` 目录，使用 async 模板以匹配 asyncpg。

- [ ] **步骤 2：创建模型**

创建 `backend/app/models/user.py`：

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

创建 `backend/app/models/tag.py`：

```python
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.post import Post


class Tag(Base):
    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    slug: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)

    posts: Mapped[list["Post"]] = relationship(
        secondary="post_tags", back_populates="tags"
    )
```

创建 `backend/app/models/post.py`：

```python
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Table,
    Text,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base

if TYPE_CHECKING:
    from app.models.tag import Tag

post_tags = Table(
    "post_tags",
    Base.metadata,
    Column(
        "post_id",
        BigInteger,
        ForeignKey("posts.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "tag_id",
        BigInteger,
        ForeignKey("tags.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    slug: Mapped[str] = mapped_column(String(200), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    excerpt: Mapped[str] = mapped_column(
        String(500), nullable=False, default="", server_default=text("''")
    )
    content_md: Mapped[str] = mapped_column(Text, nullable=False)
    cover_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    language: Mapped[str] = mapped_column(
        String(5), nullable=False, default="zh", server_default="zh"
    )
    status: Mapped[str] = mapped_column(
        String(10), nullable=False, default="draft", server_default="draft"
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    view_count: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, server_default="0"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    tags: Mapped[list["Tag"]] = relationship(
        secondary=post_tags, back_populates="posts", lazy="selectin"
    )
```

修改 `backend/app/models/__init__.py`：

```python
from app.models.post import Post, post_tags
from app.models.tag import Tag
from app.models.user import User

__all__ = ["Post", "Tag", "User", "post_tags"]
```

- [ ] **步骤 3：配置 Alembic**

用下面内容覆盖 `backend/alembic/env.py`：

```python
import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from app import models  # noqa: F401
from app.core.config import get_settings
from app.db.base import Base

config = context.config
config.set_main_option(
    "sqlalchemy.url", get_settings().database_url.replace("%", "%%")
)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
```

创建 `backend/alembic/versions/0001_initial.py`：

```python
"""initial schema

Revision ID: 0001_initial
Revises:
Create Date: 2026-10-19
"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("username", sa.String(50), nullable=False, unique=True),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "posts",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("slug", sa.String(200), nullable=False, unique=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column(
            "excerpt",
            sa.String(500),
            nullable=False,
            server_default=sa.text("''"),
        ),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("cover_url", sa.String(500), nullable=True),
        sa.Column("language", sa.String(5), nullable=False, server_default="zh"),
        sa.Column("status", sa.String(10), nullable=False, server_default="draft"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("view_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.CheckConstraint("language IN ('zh','en')", name="ck_posts_language"),
        sa.CheckConstraint(
            "status IN ('draft','published')", name="ck_posts_status"
        ),
    )
    op.create_table(
        "tags",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("name", sa.String(50), nullable=False, unique=True),
        sa.Column("slug", sa.String(50), nullable=False, unique=True),
    )
    op.create_table(
        "post_tags",
        sa.Column(
            "post_id",
            sa.BigInteger(),
            sa.ForeignKey("posts.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tags.id", ondelete="CASCADE"),
            primary_key=True,
        ),
    )
    op.create_index(
        "ix_posts_status_published_at", "posts", ["status", "published_at"]
    )
    op.execute(
        "CREATE INDEX ix_posts_title_trgm ON posts USING gin (title gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_posts_excerpt_trgm ON posts USING gin (excerpt gin_trgm_ops)"
    )
    op.execute(
        "CREATE INDEX ix_posts_content_trgm ON posts USING gin (content_md gin_trgm_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_posts_content_trgm")
    op.execute("DROP INDEX IF EXISTS ix_posts_excerpt_trgm")
    op.execute("DROP INDEX IF EXISTS ix_posts_title_trgm")
    op.drop_index("ix_posts_status_published_at", table_name="posts")
    op.drop_table("post_tags")
    op.drop_table("tags")
    op.drop_table("posts")
    op.drop_table("users")
```

解释：`pg_trgm` 扩展已在任务 2 的步骤 1 和之前的开发库中创建；迁移只负责建 trigram 索引。

- [ ] **步骤 4：执行迁移**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m alembic upgrade head
```

预期：输出 `Running upgrade -> 0001_initial`，无报错。

- [ ] **步骤 5：验证表结构**

```bash
psql -U blog_user -d my_blog -h 127.0.0.1 -c "\dt"
psql -U blog_user -d my_blog -h 127.0.0.1 -c "\d posts"
```

预期：看到 `users`、`posts`、`tags`、`post_tags` 四张表；`posts` 有 trigram 索引。

- [ ] **步骤 6：扩展测试夹具**

用下面内容覆盖 `backend/tests/conftest.py`：

```python
from pathlib import Path

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
    app.dependency_overrides.clear()
```

- [ ] **步骤 7：运行现有测试**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest -v
```

预期：`test_health` 通过。

- [ ] **步骤 8：Commit**

```bash
cd "Z:/my_blog"
git add backend/app/models backend/alembic backend/alembic.ini backend/tests/conftest.py
git commit -m "feat: add database models and initial migration"
```

---

### 任务 4：管理员种子与认证（TDD）

> 实现注记：实际实现补充了并发安全的 `try_acquire` 限流、登出 Cookie 属性、Argon2 线程池校验、dummy hash 防时序侧信道、Settings 密钥强度校验，以及 429/登出/Cookie 属性/无效 token 测试；以仓库代码为准。

**文件：**
- 创建：`backend/app/core/security.py`
- 创建：`backend/app/services/rate_limit.py`
- 创建：`backend/app/schemas/auth.py`
- 创建：`backend/app/schemas/site.py`
- 创建：`backend/app/api/deps.py`
- 创建：`backend/app/api/public/auth.py`
- 创建：`backend/app/api/public/site.py`
- 创建：`backend/app/scripts/create_admin.py`
- 修改：`backend/app/main.py`
- 创建：`backend/tests/test_auth.py`
- 修改：`backend/tests/conftest.py`

- [ ] **步骤 1：写失败的测试**

创建 `backend/tests/test_auth.py`：

```python
import pytest

from app.core.config import get_settings
from app.services.rate_limit import login_limiter


@pytest.fixture(autouse=True)
def reset_login_limiter():
    login_limiter.reset_all()
    yield


async def test_login_success(client, admin_user):
    settings = get_settings()
    response = await client.post(
        "/api/auth/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"username": settings.admin_username}
    assert "access_token" in response.cookies


async def test_me_requires_login(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_wrong_password(client, admin_user):
    settings = get_settings()
    response = await client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_admin_disabled_returns_404(client, monkeypatch):
    monkeypatch.setenv("ADMIN_ENABLED", "false")
    get_settings.cache_clear()
    try:
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "test-password"},
        )
        assert response.status_code == 404

        config = await client.get("/api/site/config")
        assert config.status_code == 200
        assert config.json() == {"admin_enabled": False}
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
```

在 `backend/tests/conftest.py` 末尾追加：

```python
import pytest


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
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest tests/test_auth.py -v
```

预期：FAIL，登录接口 404 或导入错误。

- [ ] **步骤 3：实现安全与限流**

创建 `backend/app/core/security.py`：

```python
from datetime import datetime, timedelta, timezone

import jwt
from pwdlib import PasswordHash

from app.core.config import get_settings

password_hasher = PasswordHash.recommended()
DUMMY_PASSWORD_HASH = password_hasher.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    return password_hasher.verify(password, password_hash)


def create_access_token(user_id: int) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user_id),
        "iat": now,
        "exp": now + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str) -> int | None:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except (jwt.PyJWTError, KeyError, ValueError):
        return None
```

创建 `backend/app/services/rate_limit.py`：

```python
from collections import defaultdict, deque
from time import monotonic


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_seconds: float) -> None:
        self.limit = limit
        self.window_seconds = window_seconds
        self._events: dict[str, deque[float]] = defaultdict(deque)

    def try_acquire(self, key: str) -> bool:
        now = monotonic()
        events = self._events[key]
        while events and now - events[0] > self.window_seconds:
            events.popleft()
        if len(events) >= self.limit:
            return False
        events.append(now)
        return True

    def reset(self, key: str) -> None:
        self._events.pop(key, None)

    def reset_all(self) -> None:
        self._events.clear()


login_limiter = SlidingWindowLimiter(limit=5, window_seconds=15 * 60)
```

- [ ] **步骤 4：实现 schema、依赖与路由**

创建 `backend/app/schemas/auth.py`：

```python
from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=50)
    password: str = Field(min_length=1, max_length=200)


class LoginResponse(BaseModel):
    username: str


class MeResponse(BaseModel):
    username: str
```

创建 `backend/app/schemas/site.py`：

```python
from pydantic import BaseModel


class SiteConfigResponse(BaseModel):
    admin_enabled: bool
```

创建 `backend/app/api/deps.py`。注意：后台关闭时 `/api/auth/me` 返回 401；登录、登出和未来的 `/api/admin/*` 返回 404。

```python
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
```

创建 `backend/app/api/public/auth.py`：

```python
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
    valid = await run_in_threadpool(
        verify_password, payload.password, password_hash
    )
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
```

创建 `backend/app/api/public/site.py`：

```python
from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.site import SiteConfigResponse

router = APIRouter(prefix="/site", tags=["site"])


@router.get("/config", response_model=SiteConfigResponse)
async def site_config() -> SiteConfigResponse:
    return SiteConfigResponse(admin_enabled=get_settings().admin_enabled)
```

修改 `backend/app/main.py`：

```python
from fastapi import FastAPI

from app.api.public import auth, site
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api")
app.include_router(site.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **步骤 5：创建管理员种子脚本**

创建 `backend/app/scripts/create_admin.py`：

```python
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
```

- [ ] **步骤 6：运行测试验证通过**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest tests/test_auth.py -v
```

预期：4 个测试全部通过。

- [ ] **步骤 7：在开发库创建管理员**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m app.scripts.create_admin
```

预期：输出 `created admin: admin`。

- [ ] **步骤 8：Commit**

```bash
cd "Z:/my_blog"
git add backend/app backend/tests/test_auth.py backend/tests/conftest.py
git commit -m "feat: add admin auth and site config endpoint"
```

---

### 任务 5：公开文章 API（TDD）

**文件：**
- 创建：`backend/app/schemas/post.py`
- 创建：`backend/app/services/posts.py`
- 创建：`backend/app/api/public/posts.py`
- 创建：`backend/app/api/public/tags.py`
- 创建：`backend/app/scripts/seed_demo.py`
- 修改：`backend/app/main.py`
- 创建：`backend/tests/test_posts.py`

- [ ] **步骤 1：写失败的测试**

创建 `backend/tests/test_posts.py`：

```python
from datetime import datetime, timezone

from app.models.post import Post
from app.models.tag import Tag


async def test_list_only_published(client, db_session):
    tag = Tag(name="后端", slug="backend")
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            Post(
                slug="published",
                title="已发布",
                excerpt="摘要",
                content_md="正文",
                language="zh",
                status="published",
                published_at=now,
                tags=[tag],
            ),
            Post(
                slug="draft",
                title="草稿",
                excerpt="",
                content_md="正文",
                language="zh",
                status="draft",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/posts")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["slug"] == "published"
    assert data["items"][0]["tags"] == [{"name": "后端", "slug": "backend"}]


async def test_post_detail(client, db_session):
    db_session.add(
        Post(
            slug="hello",
            title="Hello",
            excerpt="",
            content_md="# Hi",
            language="zh",
            status="published",
            published_at=datetime.now(timezone.utc),
        )
    )
    await db_session.commit()

    response = await client.get("/api/posts/hello")
    assert response.status_code == 200
    assert response.json()["content_md"] == "# Hi"


async def test_draft_detail_returns_404(client, db_session):
    db_session.add(
        Post(
            slug="draft-post",
            title="Draft",
            excerpt="",
            content_md="x",
            language="zh",
            status="draft",
        )
    )
    await db_session.commit()

    response = await client.get("/api/posts/draft-post")
    assert response.status_code == 404


async def test_filter_by_tag_and_language(client, db_session):
    backend = Tag(name="后端", slug="backend")
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            Post(
                slug="zh-backend",
                title="中文后端",
                excerpt="",
                content_md="x",
                language="zh",
                status="published",
                published_at=now,
                tags=[backend],
            ),
            Post(
                slug="en-other",
                title="English other",
                excerpt="",
                content_md="x",
                language="en",
                status="published",
                published_at=now,
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/posts?tag=backend&language=zh")
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()["items"]] == ["zh-backend"]


async def test_tags_count_published_posts(client, db_session):
    backend = Tag(name="后端", slug="backend")
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            Post(
                slug="published-one",
                title="Published",
                excerpt="",
                content_md="x",
                language="zh",
                status="published",
                published_at=now,
                tags=[backend],
            ),
            Post(
                slug="draft-one",
                title="Draft",
                excerpt="",
                content_md="x",
                language="zh",
                status="draft",
                tags=[backend],
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/tags")
    assert response.status_code == 200
    assert response.json() == [{"name": "后端", "slug": "backend", "post_count": 1}]
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest tests/test_posts.py -v
```

预期：FAIL，`/api/posts` 返回 404。

- [ ] **步骤 3：实现 schema 与服务**

创建 `backend/app/schemas/post.py`：

```python
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    slug: str


class TagWithCount(BaseModel):
    name: str
    slug: str
    post_count: int


class PostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    excerpt: str
    cover_url: str | None
    language: str
    published_at: datetime | None
    view_count: int
    tags: list[TagOut]


class PostListResponse(BaseModel):
    items: list[PostListItem]
    total: int
    page: int
    page_size: int


class PostDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    excerpt: str
    content_md: str
    cover_url: str | None
    language: str
    published_at: datetime | None
    updated_at: datetime
    view_count: int
    tags: list[TagOut]
```

创建 `backend/app/services/posts.py`：

```python
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.tag import Tag


async def list_published_posts(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    tag: str | None = None,
    language: str | None = None,
) -> tuple[list[Post], int]:
    filters = [Post.status == "published"]
    if tag:
        filters.append(Post.tags.any(Tag.slug == tag))
    if language:
        filters.append(Post.language == language)

    total = (
        await db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    )
    result = await db.execute(
        select(Post)
        .where(*filters)
        .order_by(Post.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique()), total


async def get_published_post(db: AsyncSession, slug: str) -> Post | None:
    result = await db.execute(
        select(Post).where(Post.slug == slug, Post.status == "published")
    )
    return result.scalar_one_or_none()
```

- [ ] **步骤 4：实现路由**

创建 `backend/app/api/public/posts.py`：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.post import PostDetail, PostListItem, PostListResponse
from app.services.posts import get_published_post, list_published_posts

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    tag: str | None = None,
    language: str | None = Query(None, pattern="^(zh|en)$"),
    db: AsyncSession = Depends(get_db),
) -> PostListResponse:
    posts, total = await list_published_posts(
        db, page=page, page_size=page_size, tag=tag, language=language
    )
    return PostListResponse(
        items=[PostListItem.model_validate(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=PostDetail)
async def get_post(slug: str, db: AsyncSession = Depends(get_db)) -> PostDetail:
    post = await get_published_post(db, slug)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return PostDetail.model_validate(post)
```

创建 `backend/app/api/public/tags.py`：

```python
from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.post import Post, post_tags
from app.models.tag import Tag
from app.schemas.post import TagWithCount

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagWithCount])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[TagWithCount]:
    result = await db.execute(
        select(Tag.name, Tag.slug, func.count(Post.id))
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .outerjoin(
            Post,
            (Post.id == post_tags.c.post_id) & (Post.status == "published"),
        )
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    return [
        TagWithCount(name=name, slug=slug, post_count=count)
        for name, slug, count in result.all()
    ]
```

修改 `backend/app/main.py`：

```python
from fastapi import FastAPI

from app.api.public import auth, posts, site, tags
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api")
app.include_router(site.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(tags.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **步骤 5：运行测试验证通过**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest -v
```

预期：健康检查、认证、文章测试全部通过。

- [ ] **步骤 6：创建演示数据脚本**

创建 `backend/app/scripts/seed_demo.py`：

```python
import asyncio
from datetime import datetime, timezone

from sqlalchemy import select

from app.db.session import SessionLocal, engine
from app.models.post import Post
from app.models.tag import Tag


async def main() -> None:
    async with SessionLocal() as db:
        tag_result = await db.execute(select(Tag).where(Tag.slug == "backend"))
        tag = tag_result.scalar_one_or_none()
        if tag is None:
            tag = Tag(name="后端", slug="backend")
            db.add(tag)
            await db.flush()

        post_result = await db.execute(
            select(Post).where(Post.slug == "first-post")
        )
        if post_result.scalar_one_or_none() is None:
            db.add(
                Post(
                    slug="first-post",
                    title="第一篇测试文章",
                    excerpt="用于本地开发验证的文章。",
                    content_md=(
                        "# 第一篇测试文章\n\n"
                        "这是用于本地开发验证的 Markdown 内容。\n\n"
                        "```python\nprint('hello')\n```\n"
                    ),
                    language="zh",
                    status="published",
                    published_at=datetime.now(timezone.utc),
                    tags=[tag],
                )
            )
            print("created demo post: first-post")
        await db.commit()
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())
```

运行：

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m app.scripts.seed_demo
```

预期：输出 `created demo post: first-post`。

- [ ] **步骤 7：手动验证 API**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

另开一个终端：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/posts
curl http://127.0.0.1:8000/api/posts/first-post
```

预期：健康检查返回 `{"status":"ok"}`；文章列表包含 `first-post`；详情返回 Markdown 内容。验证后按 `Ctrl+C` 停止 uvicorn。

- [ ] **步骤 8：Commit**

```bash
cd "Z:/my_blog"
git add backend/app/schemas/post.py backend/app/services/posts.py backend/app/api/public backend/app/scripts/seed_demo.py backend/app/main.py backend/tests/test_posts.py
git commit -m "feat: add public posts and tags API"
```

---

### 任务 6：前端国际化、站点配置与深色壳

**文件：**
- 创建：`frontend/src/i18n/routing.ts`
- 创建：`frontend/src/i18n/request.ts`
- 创建：`frontend/src/i18n/navigation.ts`
- 创建：`frontend/src/proxy.ts`
- 修改：`frontend/next.config.ts`
- 创建：`frontend/src/messages/zh.json`
- 创建：`frontend/src/messages/en.json`
- 创建：`frontend/src/content/site.ts`
- 创建：`frontend/src/lib/api.ts`
- 创建：`frontend/src/app/[locale]/layout.tsx`
- 创建：`frontend/src/components/site-header.tsx`
- 创建：`frontend/src/components/site-footer.tsx`
- 修改：`frontend/src/app/globals.css`
- 删除：`frontend/src/app/layout.tsx`、`frontend/src/app/page.tsx`
- 创建：`frontend/.env.local.example`

- [ ] **步骤 1：创建 i18n 配置**

创建 `frontend/src/i18n/routing.ts`：

```typescript
import {defineRouting} from 'next-intl/routing';

export const routing = defineRouting({
  locales: ['zh', 'en'],
  defaultLocale: 'zh'
});
```

创建 `frontend/src/i18n/navigation.ts`：

```typescript
import {createNavigation} from 'next-intl/navigation';
import {routing} from './routing';

export const {Link, redirect, usePathname, useRouter, getPathname} =
  createNavigation(routing);
```

创建 `frontend/src/i18n/request.ts`：

```typescript
import {hasLocale} from 'next-intl';
import {getRequestConfig} from 'next-intl/server';
import {routing} from './routing';

export default getRequestConfig(async ({requestLocale}) => {
  const requested = await requestLocale;
  const locale = hasLocale(routing.locales, requested)
    ? requested
    : routing.defaultLocale;

  return {
    locale,
    messages: (await import(`../messages/${locale}.json`)).default
  };
});
```

创建 `frontend/src/proxy.ts`（Next.js 16 中取代 `middleware.ts`）：

```typescript
import createMiddleware from 'next-intl/middleware';
import {routing} from './i18n/routing';

export default createMiddleware(routing);

export const config = {
  matcher: '/((?!api|trpc|_next|_vercel|.*\\..*).*)'
};
```

- [ ] **步骤 2：修改 next.config.ts**

用下面内容覆盖 `frontend/next.config.ts`：

```typescript
import type {NextConfig} from 'next';
import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./src/i18n/request.ts');
const apiBaseUrl = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';

const nextConfig: NextConfig = {
  // 关闭 create-next-app 默认开启的 Cache Components，避免动态页面需要额外 Suspense 边界。
  // 保留 Turbopack 的 Tailwind 加载规则。
  turbopack: {
    rules: {
      '*.css': {
        loaders: ['@tailwindcss/turbopack'],
        as: '*.css'
      }
    }
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${apiBaseUrl}/api/:path*`
      },
      {
        source: '/uploads/:path*',
        destination: `${apiBaseUrl}/uploads/:path*`
      }
    ];
  }
};

export default withNextIntl(nextConfig);
```

- [ ] **步骤 3：创建文案与站点配置**

创建 `frontend/src/messages/zh.json`：

```json
{
  "nav": {
    "posts": "文章",
    "github": "GitHub"
  },
  "footer": {
    "copyright": "© 2026 {name}. 用 Next.js 与 FastAPI 构建。"
  },
  "home": {
    "greeting": "你好，我是",
    "tagline": "记录遥感、水利与代码。",
    "latestPosts": "最新文章",
    "empty": "暂无文章"
  },
  "posts": {
    "title": "文章",
    "empty": "暂无文章",
    "back": "返回文章列表",
    "views": "次阅读",
    "prev": "上一页",
    "next": "下一页"
  }
}
```

创建 `frontend/src/messages/en.json`：

```json
{
  "nav": {
    "posts": "Posts",
    "github": "GitHub"
  },
  "footer": {
    "copyright": "© 2026 {name}. Built with Next.js and FastAPI."
  },
  "home": {
    "greeting": "Hi, I'm",
    "tagline": "Notes on remote sensing, water, and code.",
    "latestPosts": "Latest posts",
    "empty": "No posts yet"
  },
  "posts": {
    "title": "Posts",
    "empty": "No posts yet",
    "back": "Back to posts",
    "views": "views",
    "prev": "Previous",
    "next": "Next"
  }
}
```

创建 `frontend/src/content/site.ts`：

```typescript
export const site = {
  name: '彭科道',
  nameEn: 'Peng Kedao',
  github: 'https://github.com/your-username',
  email: 'you@example.com'
};
```

解释：把 `github` 和 `email` 换成你的真实信息；以后只改这个文件即可。

创建 `frontend/.env.local.example`：

```env
API_BASE_URL=http://127.0.0.1:8000
NEXT_PUBLIC_SITE_URL=http://localhost:3000
```

复制：

```bash
cd "Z:/my_blog/frontend"
cp .env.local.example .env.local
```

- [ ] **步骤 4：创建 API 封装**

创建 `frontend/src/lib/api.ts`：

```typescript
const API_BASE_URL = process.env.API_BASE_URL ?? 'http://127.0.0.1:8000';

export type Tag = {
  name: string;
  slug: string;
};

export type PostListItem = {
  slug: string;
  title: string;
  excerpt: string;
  cover_url: string | null;
  language: 'zh' | 'en';
  published_at: string | null;
  view_count: number;
  tags: Tag[];
};

export type PostListResponse = {
  items: PostListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type PostDetail = PostListItem & {
  content_md: string;
  updated_at: string;
};

async function fetchApi<T>(path: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {cache: 'no-store'});
  if (!response.ok) {
    throw new Error(`API ${response.status}: ${response.statusText}`);
  }
  return response.json() as Promise<T>;
}

export async function getPosts(params?: {
  page?: number;
  pageSize?: number;
  tag?: string;
  language?: string;
}): Promise<PostListResponse> {
  const search = new URLSearchParams();
  if (params?.page) search.set('page', String(params.page));
  if (params?.pageSize) search.set('page_size', String(params.pageSize));
  if (params?.tag) search.set('tag', params.tag);
  if (params?.language) search.set('language', params.language);
  const query = search.toString();
  return fetchApi<PostListResponse>(`/api/posts${query ? `?${query}` : ''}`);
}

export async function getPost(slug: string): Promise<PostDetail> {
  return fetchApi<PostDetail>(`/api/posts/${encodeURIComponent(slug)}`);
}

export async function getSiteConfig(): Promise<{admin_enabled: boolean}> {
  return fetchApi<{admin_enabled: boolean}>('/api/site/config');
}
```

- [ ] **步骤 5：删除默认根页面，创建 locale 布局**

```bash
cd "Z:/my_blog/frontend"
rm -f src/app/layout.tsx src/app/page.tsx
mkdir -p "src/app/[locale]"
```

创建 `frontend/src/app/[locale]/layout.tsx`：

```tsx
import type {Metadata} from 'next';
import {Geist, Geist_Mono} from 'next/font/google';
import {hasLocale, NextIntlClientProvider} from 'next-intl';
import {getMessages, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import 'highlight.js/styles/github-dark.css';
import '../globals.css';
import SiteFooter from '@/components/site-footer';
import SiteHeader from '@/components/site-header';
import {routing} from '@/i18n/routing';

const geistSans = Geist({variable: '--font-geist-sans', subsets: ['latin']});
const geistMono = Geist_Mono({variable: '--font-geist-mono', subsets: ['latin']});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));
}

export const metadata: Metadata = {
  title: '彭科道 | 水文与遥感',
  description: '记录遥感、水利与代码。'
};

export default async function LocaleLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  if (!hasLocale(routing.locales, locale)) {
    notFound();
  }
  setRequestLocale(locale);
  const messages = await getMessages();

  return (
    <html lang={locale}>
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        <NextIntlClientProvider messages={messages}>
          <div className="flex min-h-screen flex-col">
            <SiteHeader />
            <main className="flex-1">{children}</main>
            <SiteFooter />
          </div>
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

- [ ] **步骤 6：创建页头与页脚**

创建 `frontend/src/components/site-header.tsx`：

```tsx
import {useLocale, useTranslations} from 'next-intl';
import {Link} from '@/i18n/navigation';
import {site} from '@/content/site';

export default function SiteHeader() {
  const t = useTranslations('nav');
  const locale = useLocale();

  return (
    <header className="border-b border-border/80 bg-background/90 backdrop-blur">
      <div className="mx-auto flex max-w-5xl items-center justify-between px-4 py-4">
        <Link href="/" className="font-mono text-sm font-semibold text-accent">
          ~/{locale === 'zh' ? site.name : site.nameEn}
        </Link>
        <nav className="flex items-center gap-5 font-mono text-xs text-muted">
          <Link href="/posts" className="hover:text-foreground">
            {t('posts')}
          </Link>
          <a
            href={site.github}
            target="_blank"
            rel="noreferrer"
            className="hover:text-foreground"
          >
            {t('github')}
          </a>
          <Link
            href="/"
            locale={locale === 'zh' ? 'en' : 'zh'}
            className="rounded border border-border px-2 py-1 hover:text-foreground"
          >
            {locale === 'zh' ? 'EN' : '中文'}
          </Link>
        </nav>
      </div>
    </header>
  );
}
```

创建 `frontend/src/components/site-footer.tsx`：

```tsx
import {useTranslations} from 'next-intl';
import {site} from '@/content/site';

export default function SiteFooter() {
  const t = useTranslations('footer');

  return (
    <footer className="border-t border-border/80 py-8">
      <div className="mx-auto max-w-5xl px-4 font-mono text-xs text-muted">
        <p>{t('copyright', {name: site.name})}</p>
      </div>
    </footer>
  );
}
```

- [ ] **步骤 7：覆盖全局样式**

用下面内容覆盖 `frontend/src/app/globals.css`：

```css
@import 'tailwindcss';
@plugin '@tailwindcss/typography';

:root {
  --background: #0d1117;
  --foreground: #c9d1d9;
  --surface: #161b22;
  --muted: #8b949e;
  --border: #21262d;
  --accent: #3fb950;
}

@theme inline {
  --color-background: var(--background);
  --color-foreground: var(--foreground);
  --color-surface: var(--surface);
  --color-muted: var(--muted);
  --color-border: var(--border);
  --color-accent: var(--accent);
  --font-sans: var(--font-geist-sans);
  --font-mono: var(--font-geist-mono);
}

body {
  background: var(--background);
  color: var(--foreground);
  font-family: var(--font-geist-sans), 'Microsoft YaHei', sans-serif;
}

::selection {
  background: rgba(63, 185, 80, 0.35);
}
```

- [ ] **步骤 8：验证开发服务器**

```bash
cd "Z:/my_blog/frontend"
npm run dev
```

打开 `http://localhost:3000/zh`。

预期：深色背景、顶部导航、语言切换按钮；因为首页还没创建，主体可能显示 404 内容（首页在任务 8 创建）。

- [ ] **步骤 9：Commit**

```bash
cd "Z:/my_blog"
git add frontend/src frontend/next.config.ts frontend/.env.local.example
git commit -m "feat: add i18n, site config and dark shell"
```

注意：如果 `frontend/.env.local.example` 被 create-next-app 的 `.gitignore` 忽略，先在 `frontend/.gitignore` 末尾加 `!.env.local.example` 再提交。

---

### 任务 7：Playwright 公共浏览测试（先失败）

**文件：**
- 创建：`frontend/playwright.config.ts`
- 创建：`frontend/e2e/global-setup.ts`
- 创建：`frontend/e2e/public.spec.ts`
- 修改：`frontend/package.json`

- [ ] **步骤 1：创建 Playwright 配置**

创建 `frontend/playwright.config.ts`：

```typescript
import {defineConfig, devices} from '@playwright/test';
import path from 'node:path';

const backendDir = path.resolve(process.cwd(), '../backend');
const python =
  process.platform === 'win32' ? 'venv/Scripts/python.exe' : 'venv/bin/python';

export default defineConfig({
  testDir: './e2e',
  globalSetup: './e2e/global-setup.ts',
  fullyParallel: true,
  use: {
    baseURL: 'http://localhost:3000',
    trace: 'on-first-retry'
  },
  projects: [
    {
      name: 'chromium',
      use: {...devices['Desktop Chrome']}
    }
  ],
  webServer: [
    {
      command: `${python} -m uvicorn app.main:app --host 127.0.0.1 --port 8000`,
      cwd: backendDir,
      url: 'http://127.0.0.1:8000/api/health',
      reuseExistingServer: true,
      timeout: 60_000
    },
    {
      command: 'npm run dev',
      url: 'http://localhost:3000/zh',
      reuseExistingServer: true,
      timeout: 120_000
    }
  ]
});
```

创建 `frontend/e2e/global-setup.ts`：

```typescript
import {execFileSync} from 'node:child_process';
import path from 'node:path';

export default function globalSetup() {
  const backendDir = path.resolve(process.cwd(), '../backend');
  const python =
    process.platform === 'win32'
      ? path.join('venv', 'Scripts', 'python.exe')
      : path.join('venv', 'bin', 'python');

  execFileSync(path.join(backendDir, python), ['-m', 'app.scripts.seed_demo'], {
    cwd: backendDir,
    stdio: 'inherit'
  });
}
```

- [ ] **步骤 2：写失败的端到端测试**

创建 `frontend/e2e/public.spec.ts`：

```typescript
import {expect, test} from '@playwright/test';

test('home page loads with hero and navigation', async ({page}) => {
  await page.goto('/zh');
  await expect(page.getByRole('heading', {level: 1})).toBeVisible();
  await expect(
    page.getByRole('link', {name: '文章', exact: true})
  ).toBeVisible();
});

test('posts list and detail render seeded content', async ({page}) => {
  await page.goto('/zh');
  await page.getByRole('link', {name: '文章', exact: true}).click();
  await expect(page).toHaveURL(/\/zh\/posts$/);
  await expect(
    page.getByRole('heading', {name: /文章/})
  ).toBeVisible();

  await page
    .getByRole('link', {name: '第一篇测试文章'})
    .first()
    .click();
  await expect(
    page.getByRole('heading', {name: '第一篇测试文章'})
  ).toBeVisible();
  await expect(page.locator('pre code')).toContainText('print');
});

test('language switch changes UI copy', async ({page}) => {
  await page.goto('/zh');
  await page.getByRole('link', {name: 'EN', exact: true}).click();
  await expect(page).toHaveURL(/\/en$/);
  await expect(
    page.getByRole('link', {name: 'Posts', exact: true})
  ).toBeVisible();
});
```

- [ ] **步骤 3：添加测试脚本**

在 `frontend/package.json` 的 `scripts` 中加入：

```json
"test:e2e": "playwright test"
```

- [ ] **步骤 4：运行测试验证失败**

```bash
cd "Z:/my_blog/frontend"
npm run test:e2e
```

预期：测试失败，因为 `src/app/[locale]/page.tsx` 和文章页面尚未创建（`/zh` 返回 404 或找不到标题）。

- [ ] **步骤 5：Commit**

```bash
cd "Z:/my_blog"
git add frontend/playwright.config.ts frontend/e2e frontend/package.json frontend/package-lock.json
git commit -m "test: add failing public browsing e2e tests"
```

---

### 任务 8：首页、文章列表与详情页

**文件：**
- 创建：`frontend/src/app/[locale]/page.tsx`
- 创建：`frontend/src/app/[locale]/posts/page.tsx`
- 创建：`frontend/src/app/[locale]/posts/[slug]/page.tsx`
- 创建：`frontend/src/components/post-card.tsx`
- 创建：`frontend/src/components/markdown.tsx`

- [ ] **步骤 1：创建文章卡片与 Markdown 组件**

创建 `frontend/src/components/post-card.tsx`：

```tsx
import {Link} from '@/i18n/navigation';
import type {PostListItem} from '@/lib/api';

export default function PostCard({
  post,
  locale
}: {
  post: PostListItem;
  locale: string;
}) {
  const date = post.published_at
    ? new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        dateStyle: 'medium'
      }).format(new Date(post.published_at))
    : '';

  return (
    <article className="rounded-lg border border-border bg-surface p-5 transition hover:border-accent/60">
      <div className="flex items-center justify-between gap-4 font-mono text-xs text-muted">
        <time>{date}</time>
        <span className="rounded border border-border px-1.5 py-0.5">
          {post.language.toUpperCase()}
        </span>
      </div>
      <Link
        href={`/posts/${post.slug}`}
        className="mt-3 block text-xl font-semibold hover:text-accent"
      >
        {post.title}
      </Link>
      <p className="mt-2 text-sm text-muted">{post.excerpt}</p>
      <div className="mt-4 flex flex-wrap gap-2 font-mono text-xs text-accent">
        {post.tags.map((tag) => (
          <span key={tag.slug}>#{tag.name}</span>
        ))}
      </div>
    </article>
  );
}
```

创建 `frontend/src/components/markdown.tsx`：

```tsx
import ReactMarkdown from 'react-markdown';
import rehypeHighlight from 'rehype-highlight';
import remarkGfm from 'remark-gfm';

export function Markdown({content}: {content: string}) {
  return (
    <div className="prose prose-invert max-w-none prose-headings:font-mono prose-a:text-accent prose-code:text-accent">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
```

- [ ] **步骤 2：创建首页**

创建 `frontend/src/app/[locale]/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import PostCard from '@/components/post-card';
import {site} from '@/content/site';
import {Link} from '@/i18n/navigation';
import {getPosts, type PostListItem} from '@/lib/api';

export default async function HomePage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('home');

  const data = await getPosts({pageSize: 5}).catch(() => ({
    items: [] as PostListItem[],
    total: 0,
    page: 1,
    page_size: 5
  }));

  return (
    <section className="mx-auto max-w-5xl px-4 py-16">
      <p className="font-mono text-sm text-accent">$ whoami</p>
      <h1 className="mt-4 text-4xl font-bold tracking-tight sm:text-5xl">
        {t('greeting')}{' '}
        <span className="text-accent">
          {locale === 'zh' ? site.name : site.nameEn}
        </span>
      </h1>
      <p className="mt-4 max-w-xl text-muted">{t('tagline')}</p>

      <div className="mt-8 flex flex-wrap gap-3">
        <Link
          href="/posts"
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black hover:opacity-90"
        >
          {t('latestPosts')}
        </Link>
        <a
          href={site.github}
          target="_blank"
          rel="noreferrer"
          className="rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
        >
          GitHub
        </a>
      </div>

      <section className="mt-16">
        <h2 className="font-mono text-sm text-muted">
          &gt; {t('latestPosts')}_
        </h2>
        <div className="mt-6 grid gap-4">
          {data.items.length === 0 ? (
            <p className="text-muted">{t('empty')}</p>
          ) : (
            data.items.map((post) => (
              <PostCard key={post.slug} post={post} locale={locale} />
            ))
          )}
        </div>
      </section>
    </section>
  );
}
```

- [ ] **步骤 3：创建文章列表页**

创建 `frontend/src/app/[locale]/posts/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import PostCard from '@/components/post-card';
import {Link} from '@/i18n/navigation';
import {getPosts, type PostListItem} from '@/lib/api';

const PAGE_SIZE = 10;

export default async function PostsPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{page?: string}>;
}) {
  const {locale} = await params;
  const {page: pageParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('posts');
  const page = Math.max(1, Number(pageParam ?? '1') || 1);

  const data = await getPosts({page, pageSize: PAGE_SIZE}).catch(() => ({
    items: [] as PostListItem[],
    total: 0,
    page,
    page_size: PAGE_SIZE
  }));

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      <div className="mt-8 grid gap-4">
        {data.items.length === 0 ? (
          <p className="text-muted">{t('empty')}</p>
        ) : (
          data.items.map((post) => (
            <PostCard key={post.slug} post={post} locale={locale} />
          ))
        )}
      </div>

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link href={`/posts?page=${page - 1}`} className="hover:text-accent">
            ← {t('prev')}
          </Link>
        ) : null}
        {page * PAGE_SIZE < data.total ? (
          <Link href={`/posts?page=${page + 1}`} className="hover:text-accent">
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </section>
  );
}
```

- [ ] **步骤 4：创建文章详情页**

创建 `frontend/src/app/[locale]/posts/[slug]/page.tsx`：

```tsx
import type {Metadata} from 'next';
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import {Markdown} from '@/components/markdown';
import {Link} from '@/i18n/navigation';
import {getPost} from '@/lib/api';

export async function generateMetadata({
  params
}: {
  params: Promise<{locale: string; slug: string}>;
}): Promise<Metadata> {
  const {slug} = await params;
  const post = await getPost(slug).catch(() => null);
  if (!post) return {};
  return {title: post.title, description: post.excerpt};
}

export default async function PostDetailPage({
  params
}: {
  params: Promise<{locale: string; slug: string}>;
}) {
  const {locale, slug} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('posts');
  const post = await getPost(slug).catch(() => null);
  if (!post) notFound();

  const date = post.published_at
    ? new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
        dateStyle: 'long'
      }).format(new Date(post.published_at))
    : '';

  return (
    <article className="mx-auto max-w-3xl px-4 py-12">
      <Link href="/posts" className="font-mono text-xs text-muted hover:text-accent">
        &lt; {t('back')}
      </Link>

      <header className="mt-6 border-b border-border pb-6">
        <h1 className="text-3xl font-bold sm:text-4xl">{post.title}</h1>
        <div className="mt-3 flex flex-wrap items-center gap-3 font-mono text-xs text-muted">
          <time>{date}</time>
          <span>{post.language.toUpperCase()}</span>
          <span>
            {post.view_count} {t('views')}
          </span>
        </div>
        <div className="mt-3 flex flex-wrap gap-2 font-mono text-xs text-accent">
          {post.tags.map((tag) => (
            <span key={tag.slug}>#{tag.name}</span>
          ))}
        </div>
      </header>

      <div className="mt-8">
        <Markdown content={post.content_md} />
      </div>
    </article>
  );
}
```

- [ ] **步骤 5：运行端到端测试验证通过**

```bash
cd "Z:/my_blog/frontend"
npm run test:e2e
```

预期：3 个测试全部通过。Playwright 会自动启动 FastAPI 和 Next，并在开始时执行种子脚本。

- [ ] **步骤 6：手动验证**

```bash
cd "Z:/my_blog/frontend"
npm run dev
```

另开终端：

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

浏览器打开：

- `http://localhost:3000/zh`
- `http://localhost:3000/zh/posts`
- `http://localhost:3000/zh/posts/first-post`
- `http://localhost:3000/en`

预期：深色终端风格；首页显示预告和最新文章；文章详情正确渲染 Markdown 与代码高亮；中英文切换正常。

- [ ] **步骤 7：Commit**

```bash
cd "Z:/my_blog"
git add frontend/src
git commit -m "feat: add home, posts list and post detail pages"
```

---

### 任务 9：README 与最终验证

**文件：**
- 创建：`README.md`

- [ ] **步骤 1：创建 README**

创建 `Z:/my_blog/README.md`：

````markdown
# My Blog

个人站点：作品集 + 技术写作。前端 Next.js，后端 FastAPI，数据库 PostgreSQL。

## 本地启动

### 1. 数据库

```bash
psql -U postgres -h 127.0.0.1 -d postgres -c "CREATE DATABASE my_blog OWNER blog_user;"
psql -U postgres -h 127.0.0.1 -d my_blog -c "CREATE EXTENSION IF NOT EXISTS pg_trgm;"
```

### 2. 后端

```bash
cd backend
cp .env.example .env
# 编辑 .env：DATABASE_URL 密码、JWT_SECRET、ADMIN_PASSWORD
"venv/Scripts/python.exe" -m alembic upgrade head
"venv/Scripts/python.exe" -m app.scripts.create_admin
"venv/Scripts/python.exe" -m app.scripts.seed_demo
"venv/Scripts/python.exe" -m uvicorn app.main:app --reload --port 8000
```

### 3. 前端

```bash
cd frontend
cp .env.local.example .env.local
npm run dev
```

打开 `http://localhost:3000/zh`。

## 测试

```bash
cd backend
"venv/Scripts/python.exe" -m pytest -v

cd ../frontend
npm run test:e2e
```

## 关闭后台

在 `backend/.env` 中设置 `ADMIN_ENABLED=false` 并重启 FastAPI。公开页面不受影响。
````

- [ ] **步骤 2：运行后端全部测试**

```bash
cd "Z:/my_blog/backend"
"venv/Scripts/python.exe" -m pytest -v
```

预期：全部通过。

- [ ] **步骤 3：运行前端构建**

```bash
cd "Z:/my_blog/frontend"
npm run build
```

预期：构建成功，无 TypeScript 错误。

- [ ] **步骤 4：运行端到端测试**

```bash
cd "Z:/my_blog/frontend"
npm run test:e2e
```

预期：3 个测试全部通过。

- [ ] **步骤 5：Commit**

```bash
cd "Z:/my_blog"
git add README.md
git commit -m "docs: add local development readme"
```

---

## 完成标准

- [ ] `GET /api/health` 返回 `{"status":"ok"}`
- [ ] `alembic upgrade head` 成功，四张表存在
- [ ] 管理员种子脚本可创建/更新账号
- [ ] 登录、登出、`/api/auth/me` 正常
- [ ] `ADMIN_ENABLED=false` 时登录接口返回 404，`/api/site/config` 返回 `admin_enabled: false`
- [ ] `/api/posts` 只返回已发布文章，支持分页、标签、语言过滤
- [ ] `/api/posts/{slug}` 返回 Markdown 正文，草稿返回 404
- [ ] `/api/tags` 返回标签及已发布文章数
- [ ] `/zh` 首页、`/zh/posts`、`/zh/posts/first-post`、`/en` 可访问
- [ ] 深色终端风格、代码高亮、中英文切换正常
- [ ] 后端 pytest 全部通过
- [ ] 前端 Playwright 3 个测试全部通过
- [ ] `npm run build` 成功
