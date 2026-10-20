# 计划 2：后台文章管理实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 superpowers:subagent-driven-development（推荐）或 superpowers:executing-plans 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 在 `feature/admin-posts` 分支实现后台登录、文章 CRUD、Markdown 编辑器、图片上传与媒体库，并用 pytest 与 Playwright 验证完整闭环。

**架构：** 后端在 `/api/admin/*` 下新增受 `require_admin` 与 `require_same_origin` 保护的管理接口；前端把公开页迁入 `(site)` 路由组，新增 `admin` 路由树，服务端读数据时转发 Cookie，客户端写操作走同源 fetch。

**技术栈：** FastAPI、SQLAlchemy 2 async、Alembic、Pillow、pytest；Next.js 16 App Router、React 19、next-intl、React Hook Form、Zod、Playwright。

**规格：** `docs/superpowers/specs/2026-10-20-admin-posts-design.md`

---

## 文件结构

### 后端新增

```text
backend/app/
├── api/admin/
│   ├── __init__.py          # 汇总子路由并挂统一依赖
│   ├── posts.py             # /api/admin/posts
│   ├── tags.py              # /api/admin/tags
│   ├── uploads.py           # /api/admin/uploads
│   └── media.py             # /api/admin/media
├── models/media.py          # media 表模型
├── schemas/
│   ├── admin_tag.py         # 标签请求/响应
│   ├── admin_post.py        # 文章请求/响应
│   └── media.py             # 媒体与上传响应
├── services/
│   ├── admin_tags.py        # 标签查询/创建
│   ├── admin_posts.py       # 文章 CRUD 与发布规则
│   └── media.py             # 上传校验/保存/删除
backend/alembic/versions/0002_media.py
backend/tests/
├── test_admin_tags.py
├── test_admin_posts.py
├── test_media_model.py
└── test_admin_media.py
```

### 前端新增/修改

```text
frontend/src/
├── app/[locale]/(site)/
│   ├── layout.tsx           # 公开页头/页脚
│   ├── page.tsx             # 由 [locale]/page.tsx 迁入
│   ├── not-found.tsx        # 公开 404（保留站点壳）
│   └── posts/               # 由 [locale]/posts 迁入
├── app/[locale]/admin/
│   ├── layout.tsx
│   ├── login/page.tsx
│   └── (protected)/
│       ├── layout.tsx       # 鉴权 + 后台导航
│       ├── page.tsx         # redirect → posts
│       ├── posts/page.tsx
│       ├── posts/new/page.tsx
│       ├── posts/[id]/edit/page.tsx
│       └── media/page.tsx
├── components/admin/
│   ├── login-form.tsx
│   ├── logout-button.tsx
│   ├── delete-post-button.tsx
│   ├── markdown-editor.tsx
│   ├── post-form.tsx
│   └── media-manager.tsx
├── components/not-found-content.tsx
├── lib/admin-api.ts         # server-only 数据读取
├── lib/admin-types.ts       # 前后端共享类型
├── messages/zh.json
├── messages/en.json
└── components/site-header.tsx
frontend/e2e/admin.spec.ts
frontend/playwright.config.ts
frontend/e2e/global-setup.ts
```

---

## 任务 1：后台鉴权、Origin 校验与标签 API

**文件：**
- 修改：`backend/app/api/deps.py`
- 创建：`backend/app/schemas/admin_tag.py`
- 创建：`backend/app/services/admin_tags.py`
- 创建：`backend/app/api/admin/tags.py`
- 修改：`backend/app/api/admin/__init__.py`
- 修改：`backend/app/main.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_admin_tags.py`

- [ ] **步骤 1：在 conftest 中加后台测试夹具**

在 `backend/tests/conftest.py` 末尾追加：

```python
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
```

- [ ] **步骤 2：编写失败测试**

创建 `backend/tests/test_admin_tags.py`：

```python
from app.core.config import get_settings


async def test_admin_requires_login(client):
    response = await client.get("/api/admin/tags")
    assert response.status_code == 401


async def test_admin_disabled_returns_404(client, monkeypatch):
    monkeypatch.setenv("ADMIN_ENABLED", "false")
    get_settings.cache_clear()
    try:
        response = await client.get("/api/admin/tags")
        assert response.status_code == 404

        response = await client.post(
            "/api/admin/tags",
            json={"name": "测试", "slug": "test"},
        )
        assert response.status_code == 404
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


async def test_write_without_origin_is_forbidden(logged_in_client):
    response = await logged_in_client.post(
        "/api/admin/tags",
        json={"name": "测试标签", "slug": "test-tag"},
    )
    assert response.status_code == 403


async def test_write_with_wrong_origin_is_forbidden(admin_client):
    response = await admin_client.post(
        "/api/admin/tags",
        json={"name": "测试标签", "slug": "test-tag"},
        headers={"origin": "http://evil.example"},
    )
    assert response.status_code == 403


async def test_create_and_list_tags(admin_client):
    created = await admin_client.post(
        "/api/admin/tags",
        json={"name": "后端", "slug": "backend"},
    )
    assert created.status_code == 201
    body = created.json()
    assert body["name"] == "后端"
    assert body["slug"] == "backend"
    assert isinstance(body["id"], int)

    listed = await admin_client.get("/api/admin/tags")
    assert listed.status_code == 200
    assert listed.json() == [body]


async def test_duplicate_tag_conflicts(admin_client):
    payload = {"name": "后端", "slug": "backend"}
    assert (await admin_client.post("/api/admin/tags", json=payload)).status_code == 201

    same_slug = await admin_client.post(
        "/api/admin/tags",
        json={"name": "另一个", "slug": "backend"},
    )
    assert same_slug.status_code == 409

    same_name = await admin_client.post(
        "/api/admin/tags",
        json={"name": "后端", "slug": "another"},
    )
    assert same_name.status_code == 409


async def test_invalid_tag_slug(admin_client):
    response = await admin_client.post(
        "/api/admin/tags",
        json={"name": "中文标签", "slug": "中文"},
    )
    assert response.status_code == 422
```

- [ ] **步骤 3：运行测试验证失败**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_tags.py -q
```

预期：FAIL，`/api/admin/tags` 返回 404（路由尚不存在）。

- [ ] **步骤 4：实现鉴权与 Origin 依赖**

把 `backend/app/api/deps.py` 替换为：

```python
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
```

- [ ] **步骤 5：实现标签 schema、service 与路由**

创建 `backend/app/schemas/admin_tag.py`：

```python
from pydantic import BaseModel, ConfigDict, Field


class AdminTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")


class AdminTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
```

创建 `backend/app/services/admin_tags.py`：

```python
from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.schemas.admin_tag import AdminTagCreate


async def list_admin_tags(db: AsyncSession) -> list[Tag]:
    result = await db.execute(select(Tag).order_by(Tag.name.asc(), Tag.id.asc()))
    return list(result.scalars().all())


async def create_admin_tag(db: AsyncSession, data: AdminTagCreate) -> Tag:
    existing = await db.scalar(
        select(Tag.id).where(or_(Tag.name == data.name, Tag.slug == data.slug))
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")

    tag = Tag(name=data.name, slug=data.slug)
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")
    await db.refresh(tag)
    return tag
```

创建 `backend/app/api/admin/tags.py`：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin_tag import AdminTagCreate, AdminTagOut
from app.services.admin_tags import create_admin_tag, list_admin_tags

router = APIRouter(prefix="/tags", tags=["admin-tags"])


@router.get("", response_model=list[AdminTagOut])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[AdminTagOut]:
    tags = await list_admin_tags(db)
    return [AdminTagOut.model_validate(tag) for tag in tags]


@router.post("", response_model=AdminTagOut, status_code=201)
async def create_tag(
    payload: AdminTagCreate, db: AsyncSession = Depends(get_db)
) -> AdminTagOut:
    tag = await create_admin_tag(db, payload)
    return AdminTagOut.model_validate(tag)
```

把 `backend/app/api/admin/__init__.py` 替换为：

```python
from fastapi import APIRouter, Depends

from app.api.admin import tags
from app.api.deps import require_admin, require_same_origin

router = APIRouter(
    dependencies=[Depends(require_admin), Depends(require_same_origin)]
)
router.include_router(tags.router)
```

在 `backend/app/main.py` 中导入并挂载：

```python
from app.api import admin
from app.api.public import auth, posts, site, tags

app.include_router(admin.router, prefix="/api/admin")
```

- [ ] **步骤 6：运行测试验证通过**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_tags.py -q
```

预期：7 passed。

- [ ] **步骤 7：Commit**

```bash
cd Z:/my_blog
git add backend/app/api/deps.py backend/app/api/admin backend/app/schemas/admin_tag.py backend/app/services/admin_tags.py backend/app/main.py backend/tests/conftest.py backend/tests/test_admin_tags.py
git commit -m "feat: add admin auth, origin check and tag API"
```

---

## 任务 2：后台文章 CRUD

**文件：**
- 创建：`backend/app/schemas/admin_post.py`
- 创建：`backend/app/services/admin_posts.py`
- 创建：`backend/app/api/admin/posts.py`
- 修改：`backend/app/api/admin/__init__.py`
- 创建：`backend/tests/test_admin_posts.py`

- [ ] **步骤 1：编写失败测试**

创建 `backend/tests/test_admin_posts.py`：

```python
from datetime import datetime, timezone


async def test_create_draft(admin_client):
    response = await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "draft-post",
            "title": "草稿文章",
            "excerpt": "摘要",
            "content_md": "# 草稿",
            "language": "zh",
            "status": "draft",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["slug"] == "draft-post"
    assert body["status"] == "draft"
    assert body["published_at"] is None
    assert body["tags"] == []
    assert body["content_md"] == "# 草稿"


async def test_create_published_sets_published_at(admin_client):
    response = await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "published-post",
            "title": "已发布",
            "content_md": "正文",
            "language": "en",
            "status": "published",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["published_at"] is not None
    assert body["status"] == "published"


async def test_list_filters(admin_client):
    await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "alpha-draft",
            "title": "Alpha",
            "content_md": "x",
            "status": "draft",
        },
    )
    await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "beta-published",
            "title": "Beta",
            "content_md": "x",
            "status": "published",
        },
    )

    drafts = await admin_client.get("/api/admin/posts?status=draft")
    assert drafts.status_code == 200
    assert [item["slug"] for item in drafts.json()["items"]] == ["alpha-draft"]

    searched = await admin_client.get("/api/admin/posts?q=Bet")
    assert [item["slug"] for item in searched.json()["items"]] == [
        "beta-published"
    ]


async def test_update_publish_and_withdraw(admin_client):
    created = await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "toggle",
            "title": "切换状态",
            "content_md": "x",
            "status": "draft",
        },
    )
    post_id = created.json()["id"]

    published = await admin_client.patch(
        f"/api/admin/posts/{post_id}",
        json={"status": "published", "title": "已发布标题"},
    )
    assert published.status_code == 200
    published_at = published.json()["published_at"]
    assert published_at is not None
    assert published.json()["title"] == "已发布标题"

    withdrawn = await admin_client.patch(
        f"/api/admin/posts/{post_id}",
        json={"status": "draft"},
    )
    assert withdrawn.status_code == 200
    assert withdrawn.json()["published_at"] == published_at


async def test_slug_conflict(admin_client):
    payload = {"slug": "taken", "title": "一", "content_md": "x"}
    assert (await admin_client.post("/api/admin/posts", json=payload)).status_code == 201

    conflict = await admin_client.post(
        "/api/admin/posts",
        json={"slug": "taken", "title": "二", "content_md": "x"},
    )
    assert conflict.status_code == 409


async def test_invalid_tag_ids(admin_client):
    response = await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "bad-tags",
            "title": "坏标签",
            "content_md": "x",
            "tag_ids": [999999],
        },
    )
    assert response.status_code == 422


async def test_delete_post(admin_client):
    created = await admin_client.post(
        "/api/admin/posts",
        json={"slug": "to-delete", "title": "删除我", "content_md": "x"},
    )
    post_id = created.json()["id"]

    deleted = await admin_client.delete(f"/api/admin/posts/{post_id}")
    assert deleted.status_code == 204
    assert (await admin_client.get(f"/api/admin/posts/{post_id}")).status_code == 404


async def test_published_post_visible_publicly(admin_client, client):
    created = await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "public-after-publish",
            "title": "后台发布",
            "content_md": "# 公开",
            "status": "published",
        },
    )
    assert created.status_code == 201

    public = await client.get("/api/posts/public-after-publish")
    assert public.status_code == 200
    assert public.json()["title"] == "后台发布"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_posts.py -q
```

预期：FAIL，404 或路由不存在。

- [ ] **步骤 3：实现 schema**

创建 `backend/app/schemas/admin_post.py`：

```python
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.admin_tag import AdminTagOut

PostStatus = Literal["draft", "published"]
PostLanguage = Literal["zh", "en"]
SLUG_PATTERN = r"^[a-z0-9-]+$"


class AdminPostCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=200, pattern=SLUG_PATTERN)
    title: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(default="", max_length=500)
    content_md: str
    language: PostLanguage = "zh"
    status: PostStatus = "draft"
    tag_ids: list[int] = Field(default_factory=list)


class AdminPostUpdate(BaseModel):
    slug: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=SLUG_PATTERN
    )
    title: str | None = Field(default=None, min_length=1, max_length=200)
    excerpt: str | None = Field(default=None, max_length=500)
    content_md: str | None = None
    language: PostLanguage | None = None
    status: PostStatus | None = None
    tag_ids: list[int] | None = None


class AdminPostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    excerpt: str
    language: str
    status: str
    published_at: datetime | None
    updated_at: datetime
    tags: list[AdminTagOut]


class AdminPostListResponse(BaseModel):
    items: list[AdminPostListItem]
    total: int
    page: int
    page_size: int


class AdminPostDetail(AdminPostListItem):
    content_md: str
    created_at: datetime
```

- [ ] **步骤 4：实现 service**

创建 `backend/app/services/admin_posts.py`：

```python
from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.post import Post
from app.models.tag import Tag
from app.schemas.admin_post import AdminPostCreate, AdminPostUpdate


async def list_admin_posts(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    q: str | None = None,
) -> tuple[list[Post], int]:
    filters = []
    if status:
        filters.append(Post.status == status)
    if q:
        pattern = f"%{q}%"
        filters.append(or_(Post.title.ilike(pattern), Post.excerpt.ilike(pattern)))

    total = (
        await db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    )
    result = await db.execute(
        select(Post)
        .where(*filters)
        .options(defer(Post.content_md))
        .order_by(Post.updated_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique()), total


async def get_admin_post(db: AsyncSession, post_id: int) -> Post | None:
    result = await db.execute(select(Post).where(Post.id == post_id))
    return result.scalar_one_or_none()


async def _load_tags(db: AsyncSession, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = list(result.scalars().all())
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=422, detail="标签不存在")
    return tags


async def _ensure_slug_available(
    db: AsyncSession, slug: str, *, exclude_id: int | None = None
) -> None:
    query = select(Post.id).where(Post.slug == slug)
    if exclude_id is not None:
        query = query.where(Post.id != exclude_id)
    if await db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail="slug 已存在")


async def create_admin_post(db: AsyncSession, data: AdminPostCreate) -> Post:
    await _ensure_slug_available(db, data.slug)
    tags = await _load_tags(db, data.tag_ids)
    now = datetime.now(timezone.utc)
    post = Post(
        slug=data.slug,
        title=data.title,
        excerpt=data.excerpt,
        content_md=data.content_md,
        language=data.language,
        status=data.status,
        published_at=now if data.status == "published" else None,
        tags=tags,
    )
    db.add(post)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug 已存在")
    await db.refresh(post)
    return post


async def update_admin_post(
    db: AsyncSession, post_id: int, data: AdminPostUpdate
) -> Post:
    post = await get_admin_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    changes = data.model_dump(exclude_unset=True)
    tag_ids = changes.pop("tag_ids", None)
    changes = {key: value for key, value in changes.items() if value is not None}

    new_slug = changes.get("slug")
    if new_slug is not None and new_slug != post.slug:
        await _ensure_slug_available(db, new_slug, exclude_id=post.id)

    if changes.get("status") == "published" and post.published_at is None:
        post.published_at = datetime.now(timezone.utc)

    for field, value in changes.items():
        setattr(post, field, value)

    if tag_ids is not None:
        post.tags = await _load_tags(db, tag_ids)

    post.updated_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug 已存在")
    await db.refresh(post)
    return post


async def delete_admin_post(db: AsyncSession, post_id: int) -> None:
    post = await get_admin_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    await db.delete(post)
    await db.commit()
```

- [ ] **步骤 5：实现路由并注册**

创建 `backend/app/api/admin/posts.py`：

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin_post import (
    AdminPostCreate,
    AdminPostDetail,
    AdminPostListItem,
    AdminPostListResponse,
    AdminPostUpdate,
)
from app.services.admin_posts import (
    create_admin_post,
    delete_admin_post,
    get_admin_post,
    list_admin_posts,
    update_admin_post,
)

router = APIRouter(prefix="/posts", tags=["admin-posts"])


@router.get("", response_model=AdminPostListResponse)
async def list_posts(
    status: str | None = Query(None, pattern="^(draft|published)$"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> AdminPostListResponse:
    query = q.strip() if q else None
    posts, total = await list_admin_posts(
        db,
        page=page,
        page_size=page_size,
        status=status,
        q=query or None,
    )
    return AdminPostListResponse(
        items=[AdminPostListItem.model_validate(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AdminPostDetail, status_code=201)
async def create_post(
    payload: AdminPostCreate, db: AsyncSession = Depends(get_db)
) -> AdminPostDetail:
    post = await create_admin_post(db, payload)
    return AdminPostDetail.model_validate(post)


@router.get("/{post_id}", response_model=AdminPostDetail)
async def get_post(
    post_id: int, db: AsyncSession = Depends(get_db)
) -> AdminPostDetail:
    post = await get_admin_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return AdminPostDetail.model_validate(post)


@router.patch("/{post_id}", response_model=AdminPostDetail)
async def update_post(
    post_id: int,
    payload: AdminPostUpdate,
    db: AsyncSession = Depends(get_db),
) -> AdminPostDetail:
    post = await update_admin_post(db, post_id, payload)
    return AdminPostDetail.model_validate(post)


@router.delete("/{post_id}", status_code=204)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await delete_admin_post(db, post_id)
```

修改 `backend/app/api/admin/__init__.py`：

```python
from fastapi import APIRouter, Depends

from app.api.admin import posts, tags
from app.api.deps import require_admin, require_same_origin

router = APIRouter(
    dependencies=[Depends(require_admin), Depends(require_same_origin)]
)
router.include_router(tags.router)
router.include_router(posts.router)
```

- [ ] **步骤 6：运行测试验证通过**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_posts.py tests/test_admin_tags.py -q
```

预期：15 passed。

- [ ] **步骤 7：Commit**

```bash
cd Z:/my_blog
git add backend/app/api/admin backend/app/schemas/admin_post.py backend/app/services/admin_posts.py backend/tests/test_admin_posts.py
git commit -m "feat: add admin post CRUD API"
```

---

## 任务 3：media 模型与迁移

**文件：**
- 创建：`backend/app/models/media.py`
- 修改：`backend/app/models/__init__.py`
- 创建：`backend/alembic/versions/0002_media.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_media_model.py`

- [ ] **步骤 1：编写失败测试**

创建 `backend/tests/test_media_model.py`：

```python
from sqlalchemy import select

from app.models.media import Media


async def test_media_defaults_and_query(db_session):
    media = Media(
        filename="2026/10/example.png",
        original_name="example.png",
        mime="image/png",
        size_bytes=123,
    )
    db_session.add(media)
    await db_session.commit()
    await db_session.refresh(media)

    assert media.id is not None
    assert media.created_at is not None
    loaded = await db_session.scalar(select(Media).where(Media.id == media.id))
    assert loaded is not None
    assert loaded.filename == "2026/10/example.png"
```

- [ ] **步骤 2：运行测试验证失败**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_media_model.py -q
```

预期：FAIL，`ModuleNotFoundError: app.models.media`。

- [ ] **步骤 3：实现模型**

创建 `backend/app/models/media.py`：

```python
from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Identity, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class Media(Base):
    __tablename__ = "media"

    id: Mapped[int] = mapped_column(BigInteger, Identity(), primary_key=True)
    filename: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    original_name: Mapped[str] = mapped_column(String(255), nullable=False)
    mime: Mapped[str] = mapped_column(String(100), nullable=False)
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
```

把 `backend/app/models/__init__.py` 替换为：

```python
from app.models.media import Media
from app.models.post import Post, post_tags
from app.models.tag import Tag
from app.models.user import User

__all__ = ["Media", "Post", "Tag", "User", "post_tags"]
```

- [ ] **步骤 4：编写迁移**

创建 `backend/alembic/versions/0002_media.py`：

```python
"""add media table

Revision ID: 0002_media
Revises: 0001_initial
Create Date: 2026-10-20
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_media"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "media",
        sa.Column("id", sa.BigInteger(), sa.Identity(), primary_key=True),
        sa.Column("filename", sa.String(255), nullable=False, unique=True),
        sa.Column("original_name", sa.String(255), nullable=False),
        sa.Column("mime", sa.String(100), nullable=False),
        sa.Column("size_bytes", sa.Integer(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_table("media")
```

- [ ] **步骤 5：更新迁移冒烟测试**

在 `backend/tests/conftest.py` 中：

把 `DROP TABLE` 语句改为包含 `media`：

```python
await conn.execute(
    "DROP TABLE IF EXISTS media, post_tags, posts, tags, users, alembic_version CASCADE"
)
```

把表断言改为：

```python
assert {"users", "posts", "tags", "post_tags", "media", "alembic_version"} <= tables
```

- [ ] **步骤 6：运行测试验证通过**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_media_model.py -q
```

预期：模型测试 1 passed；会话级迁移冒烟测试同时执行并通过（表断言包含 media）。

- [ ] **步骤 7：Commit**

```bash
cd Z:/my_blog
git add backend/app/models/media.py backend/app/models/__init__.py backend/alembic/versions/0002_media.py backend/tests/conftest.py backend/tests/test_media_model.py
git commit -m "feat: add media table and migration"
```

---

## 任务 4：上传与媒体库 API

**文件：**
- 创建：`backend/app/schemas/media.py`
- 创建：`backend/app/services/media.py`
- 创建：`backend/app/api/admin/uploads.py`
- 创建：`backend/app/api/admin/media.py`
- 修改：`backend/app/api/admin/__init__.py`
- 修改：`backend/app/main.py`
- 修改：`backend/tests/conftest.py`
- 创建：`backend/tests/test_admin_media.py`

- [ ] **步骤 1：增加上传目录夹具**

在 `backend/tests/conftest.py` 末尾追加：

```python
@pytest.fixture
def upload_dir(tmp_path, monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    return tmp_path
```

- [ ] **步骤 2：编写失败测试**

创建 `backend/tests/test_admin_media.py`：

```python
from io import BytesIO

from PIL import Image


def make_png(size: tuple[int, int] = (4, 4)) -> bytes:
    buffer = BytesIO()
    Image.new("RGB", size, (255, 0, 0)).save(buffer, format="PNG")
    return buffer.getvalue()


async def test_upload_png(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("photo.png", make_png(), "image/png")},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["url"].startswith("/uploads/")
    assert body["url"].endswith(".png")
    assert body["mime"] == "image/png"
    assert body["size"] > 0
    assert (upload_dir / body["filename"]).exists()


async def test_upload_rejects_non_image(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("note.txt", b"hello", "text/plain")},
    )
    assert response.status_code == 422


async def test_upload_rejects_oversize(admin_client, upload_dir):
    response = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("big.png", b"x" * (5 * 1024 * 1024 + 1), "image/png")},
    )
    assert response.status_code == 413


async def test_list_media(admin_client, upload_dir):
    await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("one.png", make_png(), "image/png")},
    )
    await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("two.png", make_png(), "image/png")},
    )

    response = await admin_client.get("/api/admin/media")
    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 2
    assert len(body["items"]) == 2
    assert body["items"][0]["url"].startswith("/uploads/")


async def test_delete_media_removes_file(admin_client, upload_dir):
    created = await admin_client.post(
        "/api/admin/uploads",
        files={"file": ("delete-me.png", make_png(), "image/png")},
    )
    body = created.json()
    stored = upload_dir / body["filename"]
    assert stored.exists()

    listed = await admin_client.get("/api/admin/media")
    media_id = listed.json()["items"][0]["id"]

    deleted = await admin_client.delete(f"/api/admin/media/{media_id}")
    assert deleted.status_code == 204
    assert not stored.exists()
    assert (await admin_client.get("/api/admin/media")).json()["total"] == 0
```

- [ ] **步骤 3：运行测试验证失败**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_media.py -q
```

预期：FAIL，路由不存在。

- [ ] **步骤 4：实现 schema**

创建 `backend/app/schemas/media.py`：

```python
from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    url: str
    filename: str
    mime: str
    size: int


class MediaOut(BaseModel):
    id: int
    url: str
    filename: str
    original_name: str
    mime: str
    size_bytes: int
    created_at: datetime


class MediaListResponse(BaseModel):
    items: list[MediaOut]
    total: int
    page: int
    page_size: int
```

- [ ] **步骤 5：实现 service**

创建 `backend/app/services/media.py`：

```python
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.models.media import Media
from app.schemas.media import UploadResponse

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
FORMAT_MAP = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
    "GIF": (".gif", "image/gif"),
}


def _inspect_image(data: bytes) -> tuple[str, str]:
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image_format = (image.format or "").upper()
    except Exception:
        raise ValueError("不是有效图片")
    if image_format not in FORMAT_MAP:
        raise ValueError("不支持的图片格式")
    return FORMAT_MAP[image_format]


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def save_upload(db: AsyncSession, file: UploadFile) -> UploadResponse:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 5 MB")
    if not data:
        raise HTTPException(status_code=422, detail="文件为空")

    original_ext = Path(file.filename or "").suffix.lower()
    if original_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="不支持的扩展名")
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME:
        raise HTTPException(status_code=422, detail="不支持的 MIME 类型")

    try:
        extension, mime = await run_in_threadpool(_inspect_image, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = datetime.now(timezone.utc)
    relative_dir = now.strftime("%Y/%m")
    filename = f"{relative_dir}/{uuid4().hex}{extension}"
    target = Path(get_settings().upload_dir) / filename
    await run_in_threadpool(_write_file, target, data)

    media = Media(
        filename=filename,
        original_name=file.filename or f"upload{extension}",
        mime=mime,
        size_bytes=len(data),
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return UploadResponse(
        url=f"/uploads/{filename}",
        filename=filename,
        mime=mime,
        size=len(data),
    )


async def list_media(
    db: AsyncSession, *, page: int, page_size: int
) -> tuple[list[Media], int]:
    total = await db.scalar(select(func.count()).select_from(Media)) or 0
    result = await db.execute(
        select(Media)
        .order_by(Media.created_at.desc(), Media.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def delete_media(db: AsyncSession, media_id: int) -> None:
    media = await db.get(Media, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="图片不存在")

    base = Path(get_settings().upload_dir).resolve()
    target = (base / media.filename).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if target.exists():
        await run_in_threadpool(target.unlink)

    await db.delete(media)
    await db.commit()
```

- [ ] **步骤 6：实现上传与媒体路由**

创建 `backend/app/api/admin/uploads.py`：

```python
from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.media import UploadResponse
from app.services.media import save_upload

router = APIRouter(prefix="/uploads", tags=["admin-uploads"])


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    return await save_upload(db, file)
```

创建 `backend/app/api/admin/media.py`：

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.media import MediaListResponse, MediaOut
from app.services.media import delete_media, list_media

router = APIRouter(prefix="/media", tags=["admin-media"])


@router.get("", response_model=MediaListResponse)
async def list_media_items(
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> MediaListResponse:
    items, total = await list_media(db, page=page, page_size=page_size)
    return MediaListResponse(
        items=[
            MediaOut(
                id=item.id,
                url=f"/uploads/{item.filename}",
                filename=item.filename,
                original_name=item.original_name,
                mime=item.mime,
                size_bytes=item.size_bytes,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{media_id}", status_code=204)
async def delete_media_item(
    media_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    await delete_media(db, media_id)
```

把 `backend/app/api/admin/__init__.py` 替换为：

```python
from fastapi import APIRouter, Depends

from app.api.admin import media, posts, tags, uploads
from app.api.deps import require_admin, require_same_origin

router = APIRouter(
    dependencies=[Depends(require_admin), Depends(require_same_origin)]
)
router.include_router(tags.router)
router.include_router(posts.router)
router.include_router(uploads.router)
router.include_router(media.router)
```

- [ ] **步骤 7：挂载静态上传目录**

把 `backend/app/main.py` 替换为：

```python
from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import admin
from app.api.public import auth, posts, site, tags
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api")
app.include_router(site.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")

upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
```

- [ ] **步骤 8：运行测试验证通过**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_media.py -q
```

预期：5 passed。

- [ ] **步骤 9：Commit**

```bash
cd Z:/my_blog
git add backend/app/api/admin backend/app/schemas/media.py backend/app/services/media.py backend/app/main.py backend/tests/conftest.py backend/tests/test_admin_media.py
git commit -m "feat: add image upload and media library API"
```

---

## 任务 5：后端全量回归

**文件：** 无新增；修复本阶段发现的问题。

- [ ] **步骤 1：运行全量后端测试**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q
```

预期：全部 PASS（原 27 条 + 新增后台测试）。

- [ ] **步骤 2：验证迁移可重复执行**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m alembic upgrade head
"venv/Scripts/python.exe" -m alembic current
```

预期：当前版本为 `0002_media (head)`。

- [ ] **步骤 3：如无改动则跳过 Commit；有修复则提交**

```bash
cd Z:/my_blog
git add backend
git commit -m "fix: address admin backend regressions"
```

---

## 任务 6：前端路由分组重构

**文件：**
- 移动：`frontend/src/app/[locale]/page.tsx` → `frontend/src/app/[locale]/(site)/page.tsx`
- 移动：`frontend/src/app/[locale]/posts/` → `frontend/src/app/[locale]/(site)/posts/`
- 创建：`frontend/src/app/[locale]/(site)/layout.tsx`
- 创建：`frontend/src/app/[locale]/(site)/not-found.tsx`
- 创建：`frontend/src/components/not-found-content.tsx`
- 修改：`frontend/src/app/[locale]/layout.tsx`
- 修改：`frontend/src/app/[locale]/not-found.tsx`

- [ ] **步骤 1：移动公开页面**

```bash
cd 'Z:/my_blog/frontend/src/app/[locale]'
mkdir -p '(site)'
git mv page.tsx '(site)/page.tsx'
git mv posts '(site)/posts'
```

- [ ] **步骤 2：拆分布局**

把 `frontend/src/app/[locale]/layout.tsx` 替换为：

```tsx
import type {Metadata} from 'next';
import {Geist, Geist_Mono} from 'next/font/google';
import {hasLocale, NextIntlClientProvider} from 'next-intl';
import {getMessages, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import 'highlight.js/styles/github-dark.css';
import '../globals.css';
import {site} from '@/content/site';
import {routing} from '@/i18n/routing';

const geistSans = Geist({variable: '--font-geist-sans', subsets: ['latin']});
const geistMono = Geist_Mono({variable: '--font-geist-mono', subsets: ['latin']});

export function generateStaticParams() {
  return routing.locales.map((locale) => ({locale}));
}

export const metadata: Metadata = {
  metadataBase: new URL(
    process.env.NEXT_PUBLIC_SITE_URL ?? 'http://localhost:3000'
  ),
  title: site.title,
  description: site.description
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
          {children}
        </NextIntlClientProvider>
      </body>
    </html>
  );
}
```

创建 `frontend/src/app/[locale]/(site)/layout.tsx`：

```tsx
import SiteFooter from '@/components/site-footer';
import SiteHeader from '@/components/site-header';
import {getSiteConfig} from '@/lib/api';

export default async function SiteLayout({
  children
}: {
  children: React.ReactNode;
}) {
  let adminEnabled = false;
  try {
    adminEnabled = (await getSiteConfig()).admin_enabled;
  } catch {
    adminEnabled = false;
  }

  return (
    <div className="flex min-h-screen flex-col">
      <SiteHeader adminEnabled={adminEnabled} />
      <main className="flex-1">{children}</main>
      <SiteFooter />
    </div>
  );
}
```

- [ ] **步骤 3：抽出 404 内容并保留两层边界**

创建 `frontend/src/components/not-found-content.tsx`：

```tsx
import {getTranslations} from 'next-intl/server';
import {Link} from '@/i18n/navigation';

export default async function NotFoundContent() {
  const t = await getTranslations('errors');

  return (
    <section className="mx-auto max-w-3xl px-4 py-24 text-center">
      <p className="font-mono text-sm text-accent">404</p>
      <h1 className="mt-3 font-mono text-2xl text-accent">
        {t('notFoundTitle')}
      </h1>
      <p className="mt-3 text-muted">{t('notFoundDescription')}</p>
      <Link
        href="/"
        className="mt-6 inline-block rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
      >
        {t('backHome')}
      </Link>
    </section>
  );
}
```

把 `frontend/src/app/[locale]/not-found.tsx` 替换为：

```tsx
import NotFoundContent from '@/components/not-found-content';

export default function NotFound() {
  return <NotFoundContent />;
}
```

创建 `frontend/src/app/[locale]/(site)/not-found.tsx`：

```tsx
import NotFoundContent from '@/components/not-found-content';

export default function NotFound() {
  return <NotFoundContent />;
}
```

- [ ] **步骤 4：构建验证**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功，路由仍为 `/zh`、`/zh/posts`、`/zh/posts/[slug]`。

- [ ] **步骤 5：运行现有 E2E 回归**

确保 PostgreSQL 已启动；Playwright 会复用或启动服务：

```bash
cd Z:/my_blog/frontend
npm run test:e2e
```

预期：原有 4 条全部通过。

- [ ] **步骤 6：Commit**

```bash
cd Z:/my_blog
git add frontend/src/app frontend/src/components/not-found-content.tsx
git commit -m "refactor: split site and admin layouts with route group"
```

---

## 任务 7：前端依赖、后台 API 客户端与文案

**文件：**
- 修改：`frontend/package.json`、`frontend/package-lock.json`
- 创建：`frontend/src/lib/admin-types.ts`
- 创建：`frontend/src/lib/admin-api.ts`
- 修改：`frontend/src/messages/zh.json`
- 修改：`frontend/src/messages/en.json`

- [ ] **步骤 1：安装表单依赖**

```bash
cd Z:/my_blog/frontend
npm install react-hook-form zod @hookform/resolvers
```

预期：`package.json` 增加三个依赖，`package-lock.json` 更新。

- [ ] **步骤 2：创建共享类型**

创建 `frontend/src/lib/admin-types.ts`：

```ts
export type AdminTag = {
  id: number;
  name: string;
  slug: string;
};

export type AdminPostListItem = {
  id: number;
  slug: string;
  title: string;
  excerpt: string;
  language: 'zh' | 'en';
  status: 'draft' | 'published';
  published_at: string | null;
  updated_at: string;
  tags: AdminTag[];
};

export type AdminPostDetail = AdminPostListItem & {
  content_md: string;
  created_at: string;
};

export type AdminPostListResponse = {
  items: AdminPostListItem[];
  total: number;
  page: number;
  page_size: number;
};

export type MediaItem = {
  id: number;
  url: string;
  filename: string;
  original_name: string;
  mime: string;
  size_bytes: number;
  created_at: string;
};

export type MediaListResponse = {
  items: MediaItem[];
  total: number;
  page: number;
  page_size: number;
};
```

- [ ] **步骤 3：创建服务端后台 API 客户端**

创建 `frontend/src/lib/admin-api.ts`：

```ts
import 'server-only';
import {cookies} from 'next/headers';
import {ApiError} from '@/lib/api';
import type {
  AdminPostDetail,
  AdminPostListResponse,
  AdminTag,
  MediaListResponse
} from '@/lib/admin-types';

const API_BASE_URL = (
  process.env.API_BASE_URL ?? 'http://127.0.0.1:8000'
).replace(/\/+$/, '');

async function adminFetch<T>(path: string): Promise<T> {
  const cookieStore = await cookies();
  const cookie = cookieStore.toString();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: 'no-store',
    headers: cookie ? {cookie} : undefined
  });

  if (!response.ok) {
    let detail: string | undefined;
    try {
      const body = (await response.json()) as {detail?: unknown};
      if (typeof body.detail === 'string') detail = body.detail;
    } catch {
      // 非 JSON 错误体
    }
    throw new ApiError(
      `API ${response.status}: ${response.statusText}`,
      response.status,
      path,
      detail
    );
  }
  return response.json() as Promise<T>;
}

export async function getMe(): Promise<{username: string} | null> {
  try {
    return await adminFetch<{username: string}>('/api/auth/me');
  } catch (error) {
    if (error instanceof ApiError && error.status === 401) return null;
    throw error;
  }
}

export async function getAdminPosts(params?: {
  page?: number;
  pageSize?: number;
  status?: string;
  q?: string;
}): Promise<AdminPostListResponse> {
  const search = new URLSearchParams();
  if (params?.page !== undefined) search.set('page', String(params.page));
  if (params?.pageSize !== undefined)
    search.set('page_size', String(params.pageSize));
  if (params?.status) search.set('status', params.status);
  if (params?.q) search.set('q', params.q);
  const query = search.toString();
  return adminFetch<AdminPostListResponse>(
    `/api/admin/posts${query ? `?${query}` : ''}`
  );
}

export async function getAdminPost(
  id: number
): Promise<AdminPostDetail> {
  return adminFetch<AdminPostDetail>(`/api/admin/posts/${id}`);
}

export async function getAdminPostOrNull(
  id: number
): Promise<AdminPostDetail | null> {
  try {
    return await getAdminPost(id);
  } catch (error) {
    if (error instanceof ApiError && error.status === 404) return null;
    throw error;
  }
}

export async function getAdminTags(): Promise<AdminTag[]> {
  return adminFetch<AdminTag[]>('/api/admin/tags');
}

export async function getMediaList(params?: {
  page?: number;
  pageSize?: number;
}): Promise<MediaListResponse> {
  const search = new URLSearchParams();
  if (params?.page !== undefined) search.set('page', String(params.page));
  if (params?.pageSize !== undefined)
    search.set('page_size', String(params.pageSize));
  const query = search.toString();
  return adminFetch<MediaListResponse>(
    `/api/admin/media${query ? `?${query}` : ''}`
  );
}
```

- [ ] **步骤 4：补充中英文文案**

在 `frontend/src/messages/zh.json` 的 `nav` 对象中加入：

```json
"admin": "后台"
```

在顶层 `"errors"` 之后加入 `"admin"` 对象：

```json
"admin": {
  "nav": {
    "posts": "文章",
    "media": "媒体库",
    "backToSite": "返回站点",
    "logout": "退出登录"
  },
  "login": {
    "title": "后台登录",
    "username": "用户名",
    "password": "密码",
    "submit": "登录",
    "submitting": "登录中…",
    "invalid": "用户名或密码错误",
    "rateLimited": "尝试次数过多，请稍后再试",
    "failed": "登录失败，请稍后重试",
    "required": "请填写此项"
  },
  "posts": {
    "title": "文章管理",
    "new": "新建文章",
    "empty": "暂无文章",
    "all": "全部",
    "draft": "草稿",
    "published": "已发布",
    "search": "搜索",
    "searchPlaceholder": "搜索标题或摘要",
    "filter": "筛选",
    "edit": "编辑",
    "delete": "删除",
    "deleteFailed": "删除失败，请稍后重试",
    "confirmDelete": "确定删除《{title}》？此操作不可撤销。",
    "updated": "更新时间",
    "language": "语言",
    "status": "状态",
    "form": {
      "createTitle": "新建文章",
      "editTitle": "编辑文章",
      "title": "标题",
      "slug": "Slug",
      "slugHint": "仅小写字母、数字和连字符",
      "language": "语言",
      "status": "状态",
      "excerpt": "摘要",
      "tags": "标签",
      "newTag": "新建标签",
      "tagName": "标签名称",
      "tagSlug": "标签 Slug",
      "createTag": "创建标签",
      "content": "正文",
      "contentPlaceholder": "在此输入 Markdown…",
      "preview": "预览",
      "previewEmpty": "预览会显示在这里。",
      "save": "保存",
      "saving": "保存中…",
      "cancel": "取消",
      "back": "返回列表",
      "saved": "已保存",
      "slugConflict": "Slug 已被占用，请换一个",
      "invalid": "表单内容不合法，请检查",
      "saveFailed": "保存失败，请稍后重试",
      "uploadFailed": "图片上传失败",
      "uploading": "上传中…",
      "insertImage": "插入图片",
      "bold": "加粗",
      "italic": "斜体",
      "code": "行内代码",
      "link": "链接",
      "tagCreateFailed": "标签创建失败",
      "tagConflict": "标签名称或 Slug 已存在",
      "titleRequired": "请输入标题",
      "slugRequired": "请输入合法 Slug",
      "tooLong": "内容过长"
    }
  },
  "media": {
    "title": "媒体库",
    "upload": "上传图片",
    "uploading": "上传中…",
    "empty": "暂无图片",
    "copy": "复制链接",
    "copied": "已复制",
    "delete": "删除",
    "confirmDelete": "确定删除这张图片？引用它的文章会失效。",
    "deleteFailed": "删除失败，请稍后重试",
    "uploadFailed": "上传失败，请稍后重试",
    "backToPosts": "返回文章"
  }
}
```

在 `frontend/src/messages/en.json` 的 `nav` 对象中加入：

```json
"admin": "Admin"
```

在 `"errors"` 之后加入：

```json
"admin": {
  "nav": {
    "posts": "Posts",
    "media": "Media",
    "backToSite": "Back to site",
    "logout": "Log out"
  },
  "login": {
    "title": "Admin login",
    "username": "Username",
    "password": "Password",
    "submit": "Log in",
    "submitting": "Logging in…",
    "invalid": "Invalid username or password",
    "rateLimited": "Too many attempts. Please try again later.",
    "failed": "Login failed. Please try again.",
    "required": "This field is required"
  },
  "posts": {
    "title": "Posts",
    "new": "New post",
    "empty": "No posts yet",
    "all": "All",
    "draft": "Draft",
    "published": "Published",
    "search": "Search",
    "searchPlaceholder": "Search title or excerpt",
    "filter": "Filter",
    "edit": "Edit",
    "delete": "Delete",
    "deleteFailed": "Delete failed. Please try again.",
    "confirmDelete": "Delete “{title}”? This cannot be undone.",
    "updated": "Updated",
    "language": "Language",
    "status": "Status",
    "form": {
      "createTitle": "New post",
      "editTitle": "Edit post",
      "title": "Title",
      "slug": "Slug",
      "slugHint": "Lowercase letters, numbers and hyphens only",
      "language": "Language",
      "status": "Status",
      "excerpt": "Excerpt",
      "tags": "Tags",
      "newTag": "New tag",
      "tagName": "Tag name",
      "tagSlug": "Tag slug",
      "createTag": "Create tag",
      "content": "Content",
      "contentPlaceholder": "Write Markdown here…",
      "preview": "Preview",
      "previewEmpty": "Preview appears here.",
      "save": "Save",
      "saving": "Saving…",
      "cancel": "Cancel",
      "back": "Back to list",
      "saved": "Saved",
      "slugConflict": "This slug is already taken",
      "invalid": "Invalid form values",
      "saveFailed": "Save failed. Please try again.",
      "uploadFailed": "Image upload failed",
      "uploading": "Uploading…",
      "insertImage": "Insert image",
      "bold": "Bold",
      "italic": "Italic",
      "code": "Inline code",
      "link": "Link",
      "tagCreateFailed": "Tag creation failed",
      "tagConflict": "Tag name or slug already exists",
      "titleRequired": "Title is required",
      "slugRequired": "Enter a valid slug",
      "tooLong": "Too long"
    }
  },
  "media": {
    "title": "Media",
    "upload": "Upload image",
    "uploading": "Uploading…",
    "empty": "No images yet",
    "copy": "Copy link",
    "copied": "Copied",
    "delete": "Delete",
    "confirmDelete": "Delete this image? Posts referencing it will break.",
    "deleteFailed": "Delete failed. Please try again.",
    "uploadFailed": "Upload failed. Please try again.",
    "backToPosts": "Back to posts"
  }
}
```

- [ ] **步骤 5：构建验证**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功。

- [ ] **步骤 6：Commit**

```bash
cd Z:/my_blog
git add frontend/package.json frontend/package-lock.json frontend/src/lib/admin-api.ts frontend/src/lib/admin-types.ts frontend/src/messages/zh.json frontend/src/messages/en.json
git commit -m "feat: add admin API client, types and messages"
```

---

## 任务 8：登录页、后台鉴权布局与退出

**文件：**
- 创建：`frontend/src/app/[locale]/admin/layout.tsx`
- 创建：`frontend/src/app/[locale]/admin/login/page.tsx`
- 创建：`frontend/src/app/[locale]/admin/(protected)/layout.tsx`
- 创建：`frontend/src/app/[locale]/admin/(protected)/page.tsx`
- 创建：`frontend/src/components/admin/login-form.tsx`
- 创建：`frontend/src/components/admin/logout-button.tsx`

- [ ] **步骤 1：创建后台外壳与受保护布局**

创建 `frontend/src/app/[locale]/admin/layout.tsx`：

```tsx
export default function AdminLayout({
  children
}: {
  children: React.ReactNode;
}) {
  return <div className="min-h-screen">{children}</div>;
}
```

创建 `frontend/src/app/[locale]/admin/(protected)/layout.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound, redirect} from 'next/navigation';
import LogoutButton from '@/components/admin/logout-button';
import {Link} from '@/i18n/navigation';
import {getMe} from '@/lib/admin-api';
import {getSiteConfig} from '@/lib/api';

export default async function AdminProtectedLayout({
  children,
  params
}: {
  children: React.ReactNode;
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);

  const config = await getSiteConfig();
  if (!config.admin_enabled) notFound();

  const me = await getMe();
  if (!me) redirect(`/${locale}/admin/login`);

  const t = await getTranslations('admin.nav');

  return (
    <div className="flex min-h-screen flex-col">
      <header className="border-b border-border bg-surface">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-4">
          <nav className="flex flex-wrap items-center gap-5 font-mono text-xs">
            <span className="text-accent">~/admin</span>
            <Link href="/admin/posts" className="hover:text-accent">
              {t('posts')}
            </Link>
            <Link href="/admin/media" className="hover:text-accent">
              {t('media')}
            </Link>
            <Link href="/" className="hover:text-accent">
              {t('backToSite')}
            </Link>
          </nav>
          <div className="flex items-center gap-4 font-mono text-xs text-muted">
            <span>{me.username}</span>
            <LogoutButton />
          </div>
        </div>
      </header>
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-8">
        {children}
      </main>
    </div>
  );
}
```

创建 `frontend/src/app/[locale]/admin/(protected)/page.tsx`：

```tsx
import {redirect} from 'next/navigation';

export default async function AdminIndexPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  redirect(`/${locale}/admin/posts`);
}
```

- [ ] **步骤 2：创建退出按钮**

创建 `frontend/src/components/admin/logout-button.tsx`：

```tsx
'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';

export default function LogoutButton() {
  const t = useTranslations('admin.nav');
  const locale = useLocale();
  const router = useRouter();

  async function logout() {
    await fetch('/api/auth/logout', {method: 'POST'});
    router.replace(`/${locale}/admin/login`);
    router.refresh();
  }

  return (
    <button
      type="button"
      onClick={logout}
      className="hover:text-accent"
    >
      {t('logout')}
    </button>
  );
}
```

- [ ] **步骤 3：创建登录表单与登录页**

创建 `frontend/src/components/admin/login-form.tsx`：

```tsx
'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useState} from 'react';
import {useForm} from 'react-hook-form';
import {z} from 'zod';

const loginSchema = z.object({
  username: z.string().min(1),
  password: z.string().min(1)
});

type LoginValues = z.infer<typeof loginSchema>;

export default function LoginForm() {
  const t = useTranslations('admin.login');
  const locale = useLocale();
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const {
    register,
    handleSubmit,
    formState: {errors, isSubmitting}
  } = useForm<LoginValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {username: '', password: ''}
  });

  async function onSubmit(values: LoginValues) {
    setError(null);
    const response = await fetch('/api/auth/login', {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify(values)
    });

    if (response.ok) {
      router.replace(`/${locale}/admin/posts`);
      router.refresh();
      return;
    }
    if (response.status === 401) {
      setError(t('invalid'));
    } else if (response.status === 429) {
      setError(t('rateLimited'));
    } else {
      setError(t('failed'));
    }
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="mt-6 grid gap-4">
      <label className="grid gap-1 font-mono text-sm">
        <span>{t('username')}</span>
        <input
          id="username"
          autoComplete="username"
          {...register('username')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        {errors.username ? (
          <span className="text-xs text-red-400">{t('required')}</span>
        ) : null}
      </label>

      <label className="grid gap-1 font-mono text-sm">
        <span>{t('password')}</span>
        <input
          id="password"
          type="password"
          autoComplete="current-password"
          {...register('password')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        {errors.password ? (
          <span className="text-xs text-red-400">{t('required')}</span>
        ) : null}
      </label>

      {error ? <p className="font-mono text-xs text-red-400">{error}</p> : null}

      <button
        type="submit"
        disabled={isSubmitting}
        className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
      >
        {isSubmitting ? t('submitting') : t('submit')}
      </button>
    </form>
  );
}
```

创建 `frontend/src/app/[locale]/admin/login/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound, redirect} from 'next/navigation';
import LoginForm from '@/components/admin/login-form';
import {getMe} from '@/lib/admin-api';
import {getSiteConfig} from '@/lib/api';

export default async function AdminLoginPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);

  const config = await getSiteConfig();
  if (!config.admin_enabled) notFound();

  const me = await getMe();
  if (me) redirect(`/${locale}/admin/posts`);

  const t = await getTranslations('admin.login');

  return (
    <div className="mx-auto flex min-h-screen max-w-sm flex-col justify-center px-4">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
      <LoginForm />
    </div>
  );
}
```

- [ ] **步骤 4：构建验证**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功，`/zh/admin`、`/zh/admin/login` 可生成。

- [ ] **步骤 5：Commit**

```bash
cd Z:/my_blog
git add 'frontend/src/app/[locale]/admin' frontend/src/components/admin/login-form.tsx frontend/src/components/admin/logout-button.tsx
git commit -m "feat: add admin login and protected layout"
```

---

## 任务 9：后台文章列表

**文件：**
- 创建：`frontend/src/app/[locale]/admin/(protected)/posts/page.tsx`
- 创建：`frontend/src/components/admin/delete-post-button.tsx`

- [ ] **步骤 1：创建删除按钮**

创建 `frontend/src/components/admin/delete-post-button.tsx`：

```tsx
'use client';

import {useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';

export default function DeletePostButton({
  id,
  title
}: {
  id: number;
  title: string;
}) {
  const t = useTranslations('admin.posts');
  const router = useRouter();

  async function onDelete() {
    if (!window.confirm(t('confirmDelete', {title}))) return;
    const response = await fetch(`/api/admin/posts/${id}`, {
      method: 'DELETE'
    });
    if (response.ok || response.status === 404) {
      router.refresh();
      return;
    }
    window.alert(t('deleteFailed'));
  }

  return (
    <button
      type="button"
      onClick={onDelete}
      className="text-red-400 hover:underline"
    >
      {t('delete')}
    </button>
  );
}
```

- [ ] **步骤 2：创建列表页**

创建 `frontend/src/app/[locale]/admin/(protected)/posts/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import DeletePostButton from '@/components/admin/delete-post-button';
import {Link} from '@/i18n/navigation';
import {getAdminPosts} from '@/lib/admin-api';

const PAGE_SIZE = 10;

function formatDate(value: string, locale: string) {
  return new Intl.DateTimeFormat(locale === 'zh' ? 'zh-CN' : 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
    timeZone: 'Asia/Shanghai'
  }).format(new Date(value));
}

export default async function AdminPostsPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{
    page?: string | string[];
    status?: string | string[];
    q?: string | string[];
  }>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('admin.posts');
  const sp = await searchParams;

  const rawPage = Array.isArray(sp.page) ? sp.page[0] : sp.page;
  const parsedPage = Number(rawPage);
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const rawStatus = Array.isArray(sp.status) ? sp.status[0] : sp.status;
  const status =
    rawStatus === 'draft' || rawStatus === 'published' ? rawStatus : undefined;

  const rawQ = Array.isArray(sp.q) ? sp.q[0] : sp.q;
  const q = rawQ?.trim() || undefined;

  const data = await getAdminPosts({page, pageSize: PAGE_SIZE, status, q});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));

  function pageHref(target: number) {
    const search = new URLSearchParams();
    if (status) search.set('status', status);
    if (q) search.set('q', q);
    search.set('page', String(target));
    return `/admin/posts?${search.toString()}`;
  }

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
        <Link
          href="/admin/posts/new"
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black hover:opacity-90"
        >
          {t('new')}
        </Link>
      </div>

      <form className="mt-6 flex flex-wrap items-end gap-3 font-mono text-xs">
        <label className="grid gap-1">
          <span className="text-muted">{t('status')}</span>
          <select
            name="status"
            defaultValue={status ?? ''}
            className="rounded border border-border bg-surface px-3 py-2"
          >
            <option value="">{t('all')}</option>
            <option value="draft">{t('draft')}</option>
            <option value="published">{t('published')}</option>
          </select>
        </label>
        <label className="grid gap-1">
          <span className="text-muted">{t('search')}</span>
          <input
            name="q"
            defaultValue={q ?? ''}
            placeholder={t('searchPlaceholder')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
        </label>
        <button
          type="submit"
          className="rounded border border-border px-4 py-2 hover:border-accent"
        >
          {t('filter')}
        </button>
      </form>

      <div className="mt-6 grid gap-3">
        {data.items.length === 0 ? (
          <p className="text-muted">{t('empty')}</p>
        ) : (
          data.items.map((post) => (
            <article
              key={post.id}
              data-testid={`admin-post-${post.id}`}
              className="rounded border border-border bg-surface p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-4">
                <div>
                  <h2 className="font-semibold">
                    <Link
                      href={`/admin/posts/${post.id}/edit`}
                      className="hover:text-accent"
                    >
                      {post.title}
                    </Link>
                  </h2>
                  <p className="mt-1 font-mono text-xs text-muted">
                    {post.slug} · {post.language.toUpperCase()} ·{' '}
                    {t('updated')} {formatDate(post.updated_at, locale)}
                  </p>
                </div>
                <div className="flex items-center gap-3 font-mono text-xs">
                  <span
                    className={
                      post.status === 'published'
                        ? 'rounded border border-accent/60 px-1.5 py-0.5 text-accent'
                        : 'rounded border border-border px-1.5 py-0.5 text-muted'
                    }
                  >
                    {t(post.status)}
                  </span>
                  <Link
                    href={`/admin/posts/${post.id}/edit`}
                    className="hover:text-accent"
                  >
                    {t('edit')}
                  </Link>
                  <DeletePostButton id={post.id} title={post.title} />
                </div>
              </div>
            </article>
          ))
        )}
      </div>

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link href={pageHref(page - 1)} className="hover:text-accent">
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link href={pageHref(page + 1)} className="hover:text-accent">
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </section>
  );
}
```

注意：列表分页文案复用 `posts.prev` / `posts.next`，需补键。在 `zh.json` 的 `admin.posts` 中加：

```json
"prev": "上一页",
"next": "下一页"
```

在 `en.json` 的 `admin.posts` 中加：

```json
"prev": "Previous",
"next": "Next"
```

- [ ] **步骤 3：构建验证**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功。

- [ ] **步骤 4：Commit**

```bash
cd Z:/my_blog
git add 'frontend/src/app/[locale]/admin/(protected)/posts/page.tsx' frontend/src/components/admin/delete-post-button.tsx frontend/src/messages/zh.json frontend/src/messages/en.json
git commit -m "feat: add admin post list"
```

---

## 任务 10：Markdown 编辑器与文章表单

**文件：**
- 创建：`frontend/src/components/admin/markdown-editor.tsx`
- 创建：`frontend/src/components/admin/post-form.tsx`
- 创建：`frontend/src/app/[locale]/admin/(protected)/posts/new/page.tsx`
- 创建：`frontend/src/app/[locale]/admin/(protected)/posts/[id]/edit/page.tsx`

- [ ] **步骤 1：创建 Markdown 编辑器**

创建 `frontend/src/components/admin/markdown-editor.tsx`：

```tsx
'use client';

import {useTranslations} from 'next-intl';
import {useRef, useState} from 'react';
import {Markdown} from '@/components/markdown';

export default function MarkdownEditor({
  value,
  onChange
}: {
  value: string;
  onChange: (value: string) => void;
}) {
  const t = useTranslations('admin.posts.form');
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function insert(before: string, after: string, fallback: string) {
    const textarea = textareaRef.current;
    if (!textarea) return;
    const start = textarea.selectionStart;
    const end = textarea.selectionEnd;
    const selected = value.slice(start, end) || fallback;
    const next =
      value.slice(0, start) + before + selected + after + value.slice(end);
    onChange(next);
    requestAnimationFrame(() => {
      textarea.focus();
      textarea.setSelectionRange(
        start + before.length,
        start + before.length + selected.length
      );
    });
  }

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setUploading(true);
    setError(null);
    const form = new FormData();
    form.append('file', file);

    const response = await fetch('/api/admin/uploads', {
      method: 'POST',
      body: form
    });
    setUploading(false);

    if (!response.ok) {
      setError(t('uploadFailed'));
      return;
    }
    const data = (await response.json()) as {url: string};
    insert('![', `](${data.url})`, file.name);
  }

  return (
    <div className="grid gap-4 lg:grid-cols-2">
      <div>
        <div className="mb-2 flex flex-wrap gap-2 font-mono text-xs">
          <button
            type="button"
            onClick={() => insert('**', '**', t('bold'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('bold')}
          </button>
          <button
            type="button"
            onClick={() => insert('_', '_', t('italic'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('italic')}
          </button>
          <button
            type="button"
            onClick={() => insert('`', '`', t('code'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('code')}
          </button>
          <button
            type="button"
            onClick={() => insert('[', '](https://)', t('link'))}
            className="rounded border border-border px-2 py-1 hover:border-accent"
          >
            {t('link')}
          </button>
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
            className="rounded border border-border px-2 py-1 hover:border-accent disabled:opacity-60"
          >
            {uploading ? t('uploading') : t('insertImage')}
          </button>
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            onChange={onFileChange}
            className="hidden"
          />
        </div>

        <textarea
          id="content_md"
          ref={textareaRef}
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={20}
          placeholder={t('contentPlaceholder')}
          className="w-full rounded border border-border bg-surface p-3 font-mono text-sm"
        />
        {error ? (
          <p className="mt-2 font-mono text-xs text-red-400">{error}</p>
        ) : null}
      </div>

      <div>
        <div className="mb-2 font-mono text-xs text-muted">{t('preview')}</div>
        <div className="min-h-40 rounded border border-border bg-surface p-3">
          {value ? (
            <Markdown content={value} />
          ) : (
            <p className="text-sm text-muted">{t('previewEmpty')}</p>
          )}
        </div>
      </div>
    </div>
  );
}
```

- [ ] **步骤 2：创建文章表单**

创建 `frontend/src/components/admin/post-form.tsx`：

```tsx
'use client';

import {zodResolver} from '@hookform/resolvers/zod';
import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useEffect, useState} from 'react';
import {Controller, useForm} from 'react-hook-form';
import {z} from 'zod';
import MarkdownEditor from '@/components/admin/markdown-editor';
import {Link} from '@/i18n/navigation';
import type {AdminPostDetail, AdminTag} from '@/lib/admin-types';

const postSchema = z.object({
  title: z.string().trim().min(1).max(200),
  slug: z.string().regex(/^[a-z0-9-]+$/).max(200),
  language: z.enum(['zh', 'en']),
  status: z.enum(['draft', 'published']),
  excerpt: z.string().max(500),
  content_md: z.string(),
  tag_ids: z.array(z.number())
});

type FormValues = z.infer<typeof postSchema>;

function slugify(value: string) {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-+|-+$/g, '')
    .slice(0, 200);
}

export default function PostForm({
  post,
  tags: initialTags
}: {
  post?: AdminPostDetail;
  tags: AdminTag[];
}) {
  const locale = useLocale();
  const router = useRouter();
  const t = useTranslations('admin.posts.form');
  const [tags, setTags] = useState(initialTags);
  const [slugTouched, setSlugTouched] = useState(Boolean(post));
  const [submitError, setSubmitError] = useState<string | null>(null);
  const [saved, setSaved] = useState(false);
  const [newTagName, setNewTagName] = useState('');
  const [newTagSlug, setNewTagSlug] = useState('');
  const [tagError, setTagError] = useState<string | null>(null);

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    getValues,
    formState: {errors, isSubmitting}
  } = useForm<FormValues>({
    resolver: zodResolver(postSchema),
    defaultValues: post
      ? {
          title: post.title,
          slug: post.slug,
          language: post.language,
          status: post.status,
          excerpt: post.excerpt,
          content_md: post.content_md,
          tag_ids: post.tags.map((tag) => tag.id)
        }
      : {
          title: '',
          slug: '',
          language: 'zh',
          status: 'draft',
          excerpt: '',
          content_md: '',
          tag_ids: []
        }
  });

  const title = watch('title');
  useEffect(() => {
    if (!slugTouched) {
      setValue('slug', slugify(title || ''));
    }
  }, [title, slugTouched, setValue]);

  async function onSubmit(values: FormValues) {
    setSubmitError(null);
    setSaved(false);
    const isEdit = Boolean(post);
    const response = await fetch(
      isEdit ? `/api/admin/posts/${post!.id}` : '/api/admin/posts',
      {
        method: isEdit ? 'PATCH' : 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify(values)
      }
    );

    if (response.status === 401) {
      router.replace(`/${locale}/admin/login`);
      return;
    }
    if (response.status === 409) {
      setSubmitError(t('slugConflict'));
      return;
    }
    if (response.status === 422) {
      setSubmitError(t('invalid'));
      return;
    }
    if (!response.ok) {
      setSubmitError(t('saveFailed'));
      return;
    }

    const data = (await response.json()) as AdminPostDetail;
    if (!isEdit) {
      router.replace(`/${locale}/admin/posts/${data.id}/edit`);
      router.refresh();
      return;
    }
    setSaved(true);
    router.refresh();
  }

  async function createTag() {
    setTagError(null);
    const response = await fetch('/api/admin/tags', {
      method: 'POST',
      headers: {'content-type': 'application/json'},
      body: JSON.stringify({name: newTagName, slug: newTagSlug})
    });

    if (!response.ok) {
      setTagError(
        response.status === 409 ? t('tagConflict') : t('tagCreateFailed')
      );
      return;
    }

    const tag = (await response.json()) as AdminTag;
    setTags((current) => [...current, tag]);
    setValue('tag_ids', [...getValues('tag_ids'), tag.id]);
    setNewTagName('');
    setNewTagSlug('');
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="grid gap-6">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">
          &gt; {post ? t('editTitle') : t('createTitle')}_
        </h1>
        <Link href="/admin/posts" className="font-mono text-xs text-muted hover:text-accent">
          &lt; {t('back')}
        </Link>
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('title')}</span>
          <input
            id="title"
            {...register('title')}
            className="rounded border border-border bg-surface px-3 py-2"
          />
          {errors.title ? (
            <span className="text-xs text-red-400">{t('titleRequired')}</span>
          ) : null}
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('slug')}</span>
          <input
            id="slug"
            {...register('slug', {onChange: () => setSlugTouched(true)})}
            className="rounded border border-border bg-surface px-3 py-2 font-mono"
          />
          <span className="text-xs text-muted">{t('slugHint')}</span>
          {errors.slug ? (
            <span className="text-xs text-red-400">{t('slugRequired')}</span>
          ) : null}
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('language')}</span>
          <select
            id="language"
            {...register('language')}
            className="rounded border border-border bg-surface px-3 py-2"
          >
            <option value="zh">中文</option>
            <option value="en">English</option>
          </select>
        </label>

        <label className="grid gap-1">
          <span className="font-mono text-sm">{t('status')}</span>
          <select
            id="status"
            {...register('status')}
            className="rounded border border-border bg-surface px-3 py-2"
          >
            <option value="draft">{t('statusDraft')}</option>
            <option value="published">{t('statusPublished')}</option>
          </select>
        </label>
      </div>

      <label className="grid gap-1">
        <span className="font-mono text-sm">{t('excerpt')}</span>
        <textarea
          id="excerpt"
          rows={3}
          {...register('excerpt')}
          className="rounded border border-border bg-surface px-3 py-2"
        />
        {errors.excerpt ? (
          <span className="text-xs text-red-400">{t('tooLong')}</span>
        ) : null}
      </label>

      <fieldset className="grid gap-3">
        <legend className="font-mono text-sm">{t('tags')}</legend>
        <Controller
          control={control}
          name="tag_ids"
          render={({field}) => (
            <div className="flex flex-wrap gap-3 font-mono text-xs">
              {tags.map((tag) => {
                const checked = field.value.includes(tag.id);
                return (
                  <label key={tag.id} className="flex items-center gap-1">
                    <input
                      type="checkbox"
                      checked={checked}
                      onChange={(event) =>
                        field.onChange(
                          event.target.checked
                            ? [...field.value, tag.id]
                            : field.value.filter((id) => id !== tag.id)
                        )
                      }
                    />
                    #{tag.name}
                  </label>
                );
              })}
            </div>
          )}
        />

        <div className="flex flex-wrap items-end gap-2 font-mono text-xs">
          <label className="grid gap-1">
            <span className="text-muted">{t('tagName')}</span>
            <input
              value={newTagName}
              onChange={(event) => setNewTagName(event.target.value)}
              className="rounded border border-border bg-surface px-2 py-1"
            />
          </label>
          <label className="grid gap-1">
            <span className="text-muted">{t('tagSlug')}</span>
            <input
              value={newTagSlug}
              onChange={(event) => setNewTagSlug(event.target.value)}
              className="rounded border border-border bg-surface px-2 py-1"
            />
          </label>
          <button
            type="button"
            onClick={createTag}
            disabled={!newTagName || !newTagSlug}
            className="rounded border border-border px-3 py-1 hover:border-accent disabled:opacity-60"
          >
            {t('createTag')}
          </button>
          {tagError ? (
            <span className="text-red-400">{tagError}</span>
          ) : null}
        </div>
      </fieldset>

      <div className="grid gap-2">
        <label htmlFor="content_md" className="font-mono text-sm">
          {t('content')}
        </label>
        <Controller
          control={control}
          name="content_md"
          render={({field}) => (
            <MarkdownEditor value={field.value} onChange={field.onChange} />
          )}
        />
      </div>

      {submitError ? (
        <p className="font-mono text-xs text-red-400">{submitError}</p>
      ) : null}
      {saved ? (
        <p className="font-mono text-xs text-accent">{t('saved')}</p>
      ) : null}

      <div className="flex items-center gap-3">
        <button
          type="submit"
          disabled={isSubmitting}
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
        >
          {isSubmitting ? t('saving') : t('save')}
        </button>
        <Link
          href="/admin/posts"
          className="rounded border border-border px-4 py-2 font-mono text-sm hover:border-accent"
        >
          {t('cancel')}
        </Link>
      </div>
    </form>
  );
}
```

在 `zh.json` 的 `admin.posts.form` 中补：

```json
"statusDraft": "草稿",
"statusPublished": "已发布"
```

在 `en.json` 的 `admin.posts.form` 中补：

```json
"statusDraft": "Draft",
"statusPublished": "Published"
```

- [ ] **步骤 3：创建新建与编辑页**

创建 `frontend/src/app/[locale]/admin/(protected)/posts/new/page.tsx`：

```tsx
import {setRequestLocale} from 'next-intl/server';
import PostForm from '@/components/admin/post-form';
import {getAdminTags} from '@/lib/admin-api';

export default async function NewPostPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const tags = await getAdminTags();
  return <PostForm tags={tags} />;
}
```

创建 `frontend/src/app/[locale]/admin/(protected)/posts/[id]/edit/page.tsx`：

```tsx
import {setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostForm from '@/components/admin/post-form';
import {getAdminPostOrNull, getAdminTags} from '@/lib/admin-api';

export default async function EditPostPage({
  params
}: {
  params: Promise<{locale: string; id: string}>;
}) {
  const {locale, id} = await params;
  setRequestLocale(locale);

  const postId = Number(id);
  if (!Number.isSafeInteger(postId) || postId <= 0) notFound();

  const [post, tags] = await Promise.all([
    getAdminPostOrNull(postId),
    getAdminTags()
  ]);
  if (!post) notFound();

  return <PostForm post={post} tags={tags} />;
}
```

- [ ] **步骤 4：构建验证**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功，`/zh/admin/posts/new` 与 `/zh/admin/posts/[id]/edit` 可生成。

- [ ] **步骤 5：Commit**

```bash
cd Z:/my_blog
git add frontend/src/components/admin frontend/src/messages/zh.json frontend/src/messages/en.json 'frontend/src/app/[locale]/admin/(protected)/posts'
git commit -m "feat: add markdown editor and admin post form"
```

---

## 任务 11：媒体库页面与公开页头入口

**文件：**
- 创建：`frontend/src/components/admin/media-manager.tsx`
- 创建：`frontend/src/app/[locale]/admin/(protected)/media/page.tsx`
- 修改：`frontend/src/components/site-header.tsx`
- 修改：`frontend/src/messages/zh.json`、`frontend/src/messages/en.json`

- [ ] **步骤 1：创建媒体管理器**

创建 `frontend/src/components/admin/media-manager.tsx`：

```tsx
'use client';

import Image from 'next/image';
import {useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useRef, useState} from 'react';
import type {MediaItem} from '@/lib/admin-types';

export default function MediaManager({items}: {items: MediaItem[]}) {
  const t = useTranslations('admin.media');
  const router = useRouter();
  const fileRef = useRef<HTMLInputElement>(null);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [copiedId, setCopiedId] = useState<number | null>(null);

  async function onFileChange(event: React.ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;

    setUploading(true);
    setError(null);
    const form = new FormData();
    form.append('file', file);
    const response = await fetch('/api/admin/uploads', {
      method: 'POST',
      body: form
    });
    setUploading(false);

    if (!response.ok) {
      setError(t('uploadFailed'));
      return;
    }
    router.refresh();
  }

  async function remove(id: number) {
    if (!window.confirm(t('confirmDelete'))) return;
    const response = await fetch(`/api/admin/media/${id}`, {
      method: 'DELETE'
    });
    if (response.ok || response.status === 404) {
      router.refresh();
      return;
    }
    setError(t('deleteFailed'));
  }

  async function copy(item: MediaItem) {
    await navigator.clipboard.writeText(
      `${window.location.origin}${item.url}`
    );
    setCopiedId(item.id);
    window.setTimeout(() => setCopiedId(null), 1500);
  }

  return (
    <div>
      <div className="mt-6 flex flex-wrap items-center gap-3">
        <button
          type="button"
          onClick={() => fileRef.current?.click()}
          disabled={uploading}
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
        >
          {uploading ? t('uploading') : t('upload')}
        </button>
        <input
          ref={fileRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/gif"
          onChange={onFileChange}
          className="hidden"
        />
        {error ? (
          <span className="font-mono text-xs text-red-400">{error}</span>
        ) : null}
      </div>

      {items.length === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <div className="mt-8 grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {items.map((item) => (
            <article
              key={item.id}
              className="overflow-hidden rounded border border-border bg-surface"
            >
              <Image
                src={item.url}
                alt={item.original_name}
                width={320}
                height={200}
                unoptimized
                className="h-40 w-full object-cover"
              />
              <div className="grid gap-2 p-3 font-mono text-xs">
                <p className="truncate text-muted" title={item.original_name}>
                  {item.original_name}
                </p>
                <div className="flex items-center justify-between gap-2">
                  <button
                    type="button"
                    onClick={() => copy(item)}
                    className="hover:text-accent"
                  >
                    {copiedId === item.id ? t('copied') : t('copy')}
                  </button>
                  <button
                    type="button"
                    onClick={() => remove(item.id)}
                    className="text-red-400 hover:underline"
                  >
                    {t('delete')}
                  </button>
                </div>
              </div>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
```

- [ ] **步骤 2：创建媒体库页面**

创建 `frontend/src/app/[locale]/admin/(protected)/media/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import MediaManager from '@/components/admin/media-manager';
import {Link} from '@/i18n/navigation';
import {getMediaList} from '@/lib/admin-api';

const PAGE_SIZE = 24;

export default async function AdminMediaPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{page?: string | string[]}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('admin.media');
  const sp = await searchParams;

  const rawPage = Array.isArray(sp.page) ? sp.page[0] : sp.page;
  const parsedPage = Number(rawPage);
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const data = await getMediaList({page, pageSize: PAGE_SIZE});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));

  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-4">
        <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
        <Link
          href="/admin/posts"
          className="font-mono text-xs text-muted hover:text-accent"
        >
          &lt; {t('backToPosts')}
        </Link>
      </div>

      <MediaManager items={data.items} />

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link
            href={`/admin/media?page=${page - 1}`}
            className="hover:text-accent"
          >
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link
            href={`/admin/media?page=${page + 1}`}
            className="hover:text-accent"
          >
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </section>
  );
}
```

在 `zh.json` 的 `admin.media` 中补：

```json
"prev": "上一页",
"next": "下一页"
```

在 `en.json` 的 `admin.media` 中补：

```json
"prev": "Previous",
"next": "Next"
```

- [ ] **步骤 3：公开页头增加后台入口**

把 `frontend/src/components/site-header.tsx` 替换为：

```tsx
import {useLocale, useTranslations} from 'next-intl';
import {Link} from '@/i18n/navigation';
import LocaleSwitcher from '@/components/locale-switcher';
import {site} from '@/content/site';

export default function SiteHeader({
  adminEnabled = false
}: {
  adminEnabled?: boolean;
}) {
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
          {adminEnabled ? (
            <Link href="/admin/posts" className="hover:text-foreground">
              {t('admin')}
            </Link>
          ) : null}
          <a
            href={site.github}
            target="_blank"
            rel="noreferrer"
            className="hover:text-foreground"
          >
            {t('github')}
          </a>
          <LocaleSwitcher />
        </nav>
      </div>
    </header>
  );
}
```

- [ ] **步骤 4：构建验证**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功。

- [ ] **步骤 5：Commit**

```bash
cd Z:/my_blog
git add frontend/src/components/admin/media-manager.tsx 'frontend/src/app/[locale]/admin/(protected)/media' frontend/src/components/site-header.tsx frontend/src/messages/zh.json frontend/src/messages/en.json
git commit -m "feat: add media library and admin entry"
```

---

## 任务 12：Playwright 后台主流程

**文件：**
- 修改：`frontend/playwright.config.ts`
- 修改：`frontend/e2e/global-setup.ts`
- 创建：`frontend/e2e/admin.spec.ts`

- [ ] **步骤 1：让 E2E 安全读取管理员账号**

修改 `frontend/playwright.config.ts`，在文件顶部加入读取函数并写入 `process.env`（不回显）：

```ts
import fs from 'node:fs';

function loadAdminCredentials() {
  const envPath = path.resolve(__dirname, '../backend/.env');
  const lines = fs.readFileSync(envPath, 'utf8').split(/\r?\n/);
  const values: Record<string, string> = {};
  for (const line of lines) {
    const match = /^([A-Z0-9_]+)=(.*)$/.exec(line.trim());
    if (!match) continue;
    let value = match[2];
    if (
      (value.startsWith('"') && value.endsWith('"')) ||
      (value.startsWith("'") && value.endsWith("'"))
    ) {
      value = value.slice(1, -1);
    }
    values[match[1]] = value;
  }
  return values;
}

const adminEnv = loadAdminCredentials();
process.env.E2E_ADMIN_USERNAME = adminEnv.ADMIN_USERNAME ?? 'admin';
process.env.E2E_ADMIN_PASSWORD = adminEnv.ADMIN_PASSWORD ?? '';
```

- [ ] **步骤 2：globalSetup 确保管理员存在**

在 `frontend/e2e/global-setup.ts` 的 `seed_demo` 调用之后追加：

```ts
  execFileSync(python, ['-m', 'app.scripts.create_admin'], {
    cwd: backendDir,
    stdio: 'inherit'
  });
```

- [ ] **步骤 3：编写后台 E2E**

创建 `frontend/e2e/admin.spec.ts`：

```ts
import {expect, test} from '@playwright/test';

const username = process.env.E2E_ADMIN_USERNAME ?? 'admin';
const password = process.env.E2E_ADMIN_PASSWORD ?? '';

test('admin can log in, create, publish and delete a post', async ({page}) => {
  const stamp = Date.now();
  const title = `E2E 管理员文章 ${stamp}`;
  const slug = `e2e-admin-${stamp}`;

  await page.goto('/zh');
  await expect(page.getByRole('link', {name: '后台'})).toBeVisible();

  await page.goto('/zh/admin/posts');
  await expect(page).toHaveURL(/\/zh\/admin\/login$/);

  await page.getByLabel('用户名').fill(username);
  await page.getByLabel('密码').fill(password);
  await page.getByRole('button', {name: '登录'}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/posts$/);

  await page.getByRole('link', {name: '新建文章'}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/posts\/new$/);

  await page.getByLabel('标题').fill(title);
  await page.getByLabel('Slug').fill(slug);
  await page.getByLabel('正文').fill('# E2E\n\n后台发布测试。');
  await page.getByRole('button', {name: '保存'}).click();

  await expect(page).toHaveURL(/\/zh\/admin\/posts\/\d+\/edit$/);
  const match = page.url().match(/\/admin\/posts\/(\d+)\/edit/);
  expect(match).not.toBeNull();
  const postId = match![1];

  await page.getByLabel('状态').selectOption('published');
  await page.getByRole('button', {name: '保存'}).click();
  await expect(page.getByText('已保存')).toBeVisible();

  await page.goto(`/zh/posts/${slug}`);
  await expect(page.locator('article header h1')).toHaveText(title);

  await page.goto('/zh/admin/posts');
  const row = page.getByTestId(`admin-post-${postId}`);
  await expect(row).toBeVisible();

  page.once('dialog', (dialog) => dialog.accept());
  await row.getByRole('button', {name: '删除'}).click();
  await expect(page.getByTestId(`admin-post-${postId}`)).toHaveCount(0);
});
```

- [ ] **步骤 4：运行 E2E**

```bash
cd Z:/my_blog/frontend
npm run test:e2e
```

预期：原有 4 条 + 新增 1 条全部通过。若失败，检查：
- PostgreSQL 是否 Running；
- `backend/.env` 的 `ADMIN_ENABLED=true`；
- `SITE_ORIGIN` 是否为 `http://localhost:3000`；
- 登录后 Cookie 是否通过 Next rewrite 正常写入。

- [ ] **步骤 5：Commit**

```bash
cd Z:/my_blog
git add frontend/playwright.config.ts frontend/e2e/global-setup.ts frontend/e2e/admin.spec.ts
git commit -m "test: add admin create and publish e2e flow"
```

---

## 任务 13：全量验证与文档收尾

**文件：**
- 修改：`README.md`
- 修改：`HANDOFF.md`

- [ ] **步骤 1：启动 PostgreSQL（如未运行）**

```powershell
Start-Service postgresql-x64-17
```

- [ ] **步骤 2：后端全量测试**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q
```

预期：全部 PASS。

- [ ] **步骤 3：前端构建**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：构建成功。

- [ ] **步骤 4：E2E 全量**

```bash
cd Z:/my_blog/frontend
npm run test:e2e
```

预期：5 passed。

- [ ] **步骤 5：更新 README 与 HANDOFF**

在 `README.md` 的「后台开关」之后新增一节：

```markdown
## 后台管理

启动后端并确保 `ADMIN_ENABLED=true`，打开 <http://localhost:3000/zh/admin>：

- 使用 `backend/.env` 中的管理员账号登录；
- 文章支持草稿/发布、Markdown 实时预览、正文图片上传；
- 媒体库支持上传、复制链接、删除；
- 所有 `/api/admin/*` 写操作校验 `Origin`，`SITE_ORIGIN` 必须与浏览器地址栏来源一致。
```

在 `HANDOFF.md` 的现状与已完成部分更新为：

```markdown
- 当前分支：`master`（合并后）
- 已完成：后台登录、文章 CRUD、Markdown 编辑器、图片上传与媒体库
- 验证：后端 pytest 全部通过；Playwright 5 passed；`npm run build` 成功
```

并把「尚未完成」中的后台文章管理条目移除，保留项目、评论、搜索、阅读统计、SEO、部署。

- [ ] **步骤 6：最终 Commit**

```bash
cd Z:/my_blog
git add README.md HANDOFF.md
git commit -m "docs: document admin workflow"
git status --short --branch
```

预期：工作树干净，位于 `feature/admin-posts`。

---

## 自检结果

- **规格覆盖度：** 鉴权/Origin、文章 CRUD、标签最小集、上传/媒体、路由重构、登录、编辑器、媒体库、页头入口、测试与文档均有对应任务。
- **占位符扫描：** 无 TODO/待定；所有代码步骤包含完整实现。
- **类型一致性：** 后端 `AdminTagOut`（id/name/slug）与前端 `AdminTag` 一致；`AdminPostDetail` 字段与前端类型一致；`media` 的 `filename` 始终为相对路径，URL 统一拼接 `/uploads/`。
- **范围检查：** 单个实现计划可覆盖；未包含仪表盘、封面图、项目、评论、搜索、统计与部署。
