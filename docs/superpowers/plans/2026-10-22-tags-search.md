# 标签管理与站内搜索实现计划

> **面向 AI 代理的工作者：** 必需子技能：使用 `subagent-driven-development`（推荐）或 `executing-plans` 逐任务实现此计划。步骤使用复选框（`- [ ]`）语法来跟踪进度。

**目标：** 完成后台标签的创建/改名/删除、公开标签页与文章列表标签筛选、文章+项目站内搜索。

**架构：** 后端在现有 FastAPI 分层中扩展 admin tags（新增 PATCH/DELETE 与 post_count）并新增 `/api/search`（SQLAlchemy + pg_trgm，分组返回文章与项目）；前端抽出共用 `PostList`，新增标签页、搜索页与后台标签管理页，群复用现有卡片组件。

**技术栈：** FastAPI、SQLAlchemy 2 async、PostgreSQL pg_trgm、Next.js 16 App Router、next-intl、Playwright、pytest。

**分支：** `feature/tags-search`（已创建，规格已提交 `01f4797`）

> **实施记录（2026-10-22，任务 1）：** 执行中发现 `AdminPostListItem.tags` 复用 `AdminTagOut` 会因新增必填 `post_count` 导致带标签文章序列化 500。已新增 `AdminTagRef {id,name,slug}` 供后台文章使用，`AdminTagOut` 继承它并只增加 `post_count`；回归测试在 `backend/tests/test_admin_posts.py`。前端类型需对应拆分 `AdminTagRef` 与 `AdminTag`（见任务 4）。

---

## 文件结构

**后端**

- 修改 `backend/app/schemas/admin_tag.py`：新增 `AdminTagRef`，`AdminTagOut` 继承它并增加 `post_count`，新增 `AdminTagUpdate`。
- 修改 `backend/app/schemas/admin_post.py`：`AdminPostListItem.tags` 改用 `AdminTagRef`。
- 修改 `backend/tests/test_admin_posts.py`：带标签文章序列化回归测试。
- 修改 `backend/app/services/admin_tags.py`：列表计数、更新、删除。
- 修改 `backend/app/api/admin/tags.py`：PATCH/DELETE 路由与响应组装。
- 创建 `backend/app/schemas/search.py`：`SearchResponse`。
- 创建 `backend/app/services/search.py`：LIKE 转义、文章/项目查询与排序。
- 创建 `backend/app/api/public/search.py`：`GET /api/search`。
- 修改 `backend/app/main.py`：注册搜索路由。
- 修改 `backend/tests/test_admin_tags.py`：标签管理测试。
- 创建 `backend/tests/test_search.py`：搜索测试。

**前端**

- 修改 `frontend/src/lib/api.ts`：`TagWithCount`、`getTags`、`SearchResponse`、`search`。
- 修改 `frontend/src/lib/admin-types.ts`：`AdminTag.post_count`。
- 创建 `frontend/src/components/post-list.tsx`：共用文章列表与分页。
- 修改 `frontend/src/components/post-card.tsx`：标签改为链接。
- 修改 `frontend/src/app/[locale]/(site)/posts/page.tsx`：标签 chips + 使用 `PostList`。
- 创建 `frontend/src/app/[locale]/(site)/tags/[slug]/page.tsx`：公开标签页。
- 创建 `frontend/src/app/[locale]/(site)/search/page.tsx`：搜索页。
- 修改 `frontend/src/components/site-header.tsx`：搜索入口。
- 创建 `frontend/src/app/[locale]/admin/(protected)/tags/page.tsx`：后台标签页。
- 创建 `frontend/src/components/admin/tag-manager.tsx`：后台标签管理交互。
- 修改 `frontend/src/app/[locale]/admin/(protected)/layout.tsx`：标签导航。
- 修改 `frontend/src/messages/zh.json`、`en.json`：新增文案。
- 创建 `frontend/e2e/tags.spec.ts`、`frontend/e2e/search.spec.ts`。

**文档**

- 修改 `README.md`、`HANDOFF.md`：功能、测试基线、部署状态。

---

## 任务 1：后台标签的计数、改名与删除

**文件：**
- 修改：`backend/tests/test_admin_tags.py`
- 修改：`backend/tests/test_admin_posts.py`
- 修改：`backend/app/schemas/admin_tag.py`
- 修改：`backend/app/schemas/admin_post.py`
- 修改：`backend/app/services/admin_tags.py`
- 修改：`backend/app/api/admin/tags.py`

- [ ] **步骤 1：追加失败测试**

在 `backend/tests/test_admin_tags.py` 顶部加入：

```python
from datetime import datetime, timezone

from sqlalchemy import func, select

from app.models.post import Post, post_tags
from app.models.tag import Tag
```

在文件末尾追加：

```python
async def test_admin_tag_post_count_includes_drafts(admin_client, db_session):
    tag = Tag(name="后端", slug="backend")
    now = datetime.now(timezone.utc)
    db_session.add_all(
        [
            Post(
                slug="pub",
                title="发布",
                content_md="x",
                status="published",
                published_at=now,
                tags=[tag],
            ),
            Post(slug="draft", title="草稿", content_md="x", status="draft", tags=[tag]),
        ]
    )
    await db_session.commit()

    body = (await admin_client.get("/api/admin/tags")).json()
    assert body == [
        {"id": tag.id, "name": "后端", "slug": "backend", "post_count": 2}
    ]


async def test_update_tag_name_and_slug(admin_client):
    created = (
        await admin_client.post(
            "/api/admin/tags", json={"name": "旧名", "slug": "old"}
        )
    ).json()

    renamed = await admin_client.patch(
        f"/api/admin/tags/{created['id']}", json={"name": "新名"}
    )
    assert renamed.status_code == 200
    assert renamed.json()["name"] == "新名"
    assert renamed.json()["slug"] == "old"

    reslugged = await admin_client.patch(
        f"/api/admin/tags/{created['id']}", json={"slug": "new"}
    )
    assert reslugged.status_code == 200
    assert reslugged.json()["name"] == "新名"
    assert reslugged.json()["slug"] == "new"

    same = await admin_client.patch(
        f"/api/admin/tags/{created['id']}", json={"name": "新名", "slug": "new"}
    )
    assert same.status_code == 200


async def test_update_tag_conflicts(admin_client):
    first = (
        await admin_client.post(
            "/api/admin/tags", json={"name": "后端", "slug": "backend"}
        )
    ).json()
    second = (
        await admin_client.post(
            "/api/admin/tags", json={"name": "前端", "slug": "frontend"}
        )
    ).json()

    name_conflict = await admin_client.patch(
        f"/api/admin/tags/{second['id']}", json={"name": first["name"]}
    )
    assert name_conflict.status_code == 409

    slug_conflict = await admin_client.patch(
        f"/api/admin/tags/{second['id']}", json={"slug": first["slug"]}
    )
    assert slug_conflict.status_code == 409


async def test_update_tag_validation_and_missing(admin_client):
    created = (
        await admin_client.post(
            "/api/admin/tags", json={"name": "后端", "slug": "backend"}
        )
    ).json()

    assert (
        await admin_client.patch(f"/api/admin/tags/{created['id']}", json={})
    ).status_code == 422
    assert (
        await admin_client.patch("/api/admin/tags/999999", json={"name": "x"})
    ).status_code == 404


async def test_delete_tag_detaches_posts(admin_client, db_session):
    tag = Tag(name="后端", slug="backend")
    post = Post(
        slug="keep-me",
        title="保留",
        content_md="x",
        status="published",
        published_at=datetime.now(timezone.utc),
        tags=[tag],
    )
    db_session.add(post)
    await db_session.commit()
    tag_id = tag.id
    post_id = post.id

    response = await admin_client.delete(f"/api/admin/tags/{tag_id}")
    assert response.status_code == 204

    assert (
        await db_session.scalar(
            select(func.count()).select_from(Tag).where(Tag.id == tag_id)
        )
        == 0
    )
    assert (
        await db_session.scalar(
            select(func.count()).select_from(Post).where(Post.id == post_id)
        )
        == 1
    )
    assert (
        await db_session.scalar(
            select(func.count())
            .select_from(post_tags)
            .where(post_tags.c.tag_id == tag_id)
        )
        == 0
    )


async def test_delete_missing_tag_returns_404(admin_client):
    response = await admin_client.delete("/api/admin/tags/999999")
    assert response.status_code == 404
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_tags.py -q
```

预期：新增用例失败——列表缺少 `post_count`，PATCH/DELETE 返回 405。

- [ ] **步骤 3：扩展 schema**

将 `backend/app/schemas/admin_tag.py` 全文替换为：

```python
from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdminTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")


class AdminTagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    slug: str | None = Field(
        default=None, min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$"
    )

    @model_validator(mode="after")
    def require_at_least_one(self) -> "AdminTagUpdate":
        if self.name is None and self.slug is None:
            raise ValueError("name or slug is required")
        return self


class AdminTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    post_count: int
```

- [ ] **步骤 4：扩展 service**

将 `backend/app/services/admin_tags.py` 全文替换为：

```python
from fastapi import HTTPException
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, post_tags
from app.models.tag import Tag
from app.schemas.admin_tag import AdminTagCreate, AdminTagUpdate


async def list_admin_tags(db: AsyncSession) -> list[tuple[Tag, int]]:
    result = await db.execute(
        select(Tag, func.count(Post.id))
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .outerjoin(Post, Post.id == post_tags.c.post_id)
        .group_by(Tag.id)
        .order_by(Tag.name.asc(), Tag.id.asc())
    )
    return [(tag, count) for tag, count in result.all()]


async def _tag_post_count(db: AsyncSession, tag_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(post_tags)
            .where(post_tags.c.tag_id == tag_id)
        )
        or 0
    )


async def _ensure_available(
    db: AsyncSession,
    *,
    name: str | None,
    slug: str | None,
    exclude_id: int,
) -> None:
    conditions = []
    if name is not None:
        conditions.append(Tag.name == name)
    if slug is not None:
        conditions.append(Tag.slug == slug)
    if not conditions:
        return

    existing = await db.scalar(
        select(Tag.id).where(or_(*conditions), Tag.id != exclude_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")


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


async def update_admin_tag(
    db: AsyncSession, tag_id: int, data: AdminTagUpdate
) -> tuple[Tag, int]:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")

    await _ensure_available(
        db, name=data.name, slug=data.slug, exclude_id=tag_id
    )

    if data.name is not None:
        tag.name = data.name
    if data.slug is not None:
        tag.slug = data.slug

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")
    await db.refresh(tag)
    return tag, await _tag_post_count(db, tag_id)


async def delete_admin_tag(db: AsyncSession, tag_id: int) -> None:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")

    await db.execute(sql_delete(Tag).where(Tag.id == tag_id))
    await db.commit()
```

- [ ] **步骤 5：扩展后台路由**

将 `backend/app/api/admin/tags.py` 全文替换为：

```python
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tag import Tag
from app.schemas.admin_tag import AdminTagCreate, AdminTagOut, AdminTagUpdate
from app.services.admin_tags import (
    create_admin_tag,
    delete_admin_tag,
    list_admin_tags,
    update_admin_tag,
)

router = APIRouter(prefix="/tags", tags=["admin-tags"])


def _tag_out(tag: Tag, post_count: int) -> AdminTagOut:
    return AdminTagOut(
        id=tag.id, name=tag.name, slug=tag.slug, post_count=post_count
    )


@router.get("", response_model=list[AdminTagOut])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[AdminTagOut]:
    rows = await list_admin_tags(db)
    return [_tag_out(tag, count) for tag, count in rows]


@router.post("", response_model=AdminTagOut, status_code=201)
async def create_tag(
    payload: AdminTagCreate, db: AsyncSession = Depends(get_db)
) -> AdminTagOut:
    tag = await create_admin_tag(db, payload)
    return _tag_out(tag, 0)


@router.patch("/{tag_id}", response_model=AdminTagOut)
async def update_tag(
    tag_id: int, payload: AdminTagUpdate, db: AsyncSession = Depends(get_db)
) -> AdminTagOut:
    tag, post_count = await update_admin_tag(db, tag_id, payload)
    return _tag_out(tag, post_count)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    await delete_admin_tag(db, tag_id)
```

- [ ] **步骤 6：运行测试确认通过**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_admin_tags.py -q
```

预期：全部 PASS。

- [ ] **步骤 7：Commit**

```bash
git add backend/app/schemas/admin_tag.py backend/app/schemas/admin_post.py backend/app/services/admin_tags.py backend/app/api/admin/tags.py backend/tests/test_admin_tags.py backend/tests/test_admin_posts.py
git commit -m "feat: add tag update and delete APIs with post counts"
```

---

## 任务 2：站内搜索 API

**文件：**
- 创建：`backend/tests/test_search.py`
- 创建：`backend/app/schemas/search.py`
- 创建：`backend/app/services/search.py`
- 创建：`backend/app/api/public/search.py`
- 修改：`backend/app/main.py`

- [ ] **步骤 1：编写失败测试**

创建 `backend/tests/test_search.py`：

```python
from datetime import date, datetime, timezone

from app.models.post import Post
from app.models.project import Project


def make_post(slug: str, **overrides) -> Post:
    values = {
        "slug": slug,
        "title": "文章",
        "excerpt": "",
        "content_md": "正文",
        "language": "zh",
        "status": "published",
        "published_at": datetime.now(timezone.utc),
    }
    values.update(overrides)
    return Post(**values)


def make_project(**overrides) -> Project:
    values = {
        "slug": "demo-project",
        "title_zh": "示例项目",
        "title_en": "Demo project",
        "summary_zh": "中文摘要",
        "summary_en": "English summary",
        "content_md_zh": "# 中文正文",
        "content_md_en": "# English body",
        "tech_stack": [],
        "status": "published",
        "featured": False,
        "sort_order": 0,
        "started_on": date(2026, 1, 1),
    }
    values.update(overrides)
    return Project(**values)


async def test_search_matches_title_excerpt_and_content(client, db_session):
    db_session.add_all(
        [
            make_post("title-match", title="遥感入门"),
            make_post("excerpt-match", excerpt="讲水利调度"),
            make_post("content-match", content_md="# 遥感与水利"),
        ]
    )
    await db_session.commit()

    title = await client.get("/api/search", params={"q": "遥感入门"})
    assert [item["slug"] for item in title.json()["posts"]] == ["title-match"]

    excerpt = await client.get("/api/search", params={"q": "水利调度"})
    assert [item["slug"] for item in excerpt.json()["posts"]] == ["excerpt-match"]

    content = await client.get("/api/search", params={"q": "遥感与水利"})
    assert [item["slug"] for item in content.json()["posts"]] == ["content-match"]


async def test_search_excludes_draft_posts(client, db_session):
    db_session.add(
        make_post(
            "draft",
            title="FastAPI 草稿",
            status="draft",
            published_at=None,
        )
    )
    await db_session.commit()

    response = await client.get("/api/search", params={"q": "FastAPI"})
    assert response.status_code == 200
    assert response.json() == {"posts": [], "projects": [], "total": 0}


async def test_search_projects_by_locale(client, db_session):
    db_session.add_all(
        [
            make_project(
                slug="water",
                title_zh="水体分割",
                title_en="Water segmentation",
                summary_zh="",
                summary_en="",
                content_md_zh="",
                content_md_en="",
            ),
            make_project(
                slug="draft",
                title_zh="水体草稿",
                title_en="Water draft",
                summary_zh="",
                summary_en="",
                content_md_zh="",
                content_md_en="",
                status="draft",
            ),
        ]
    )
    await db_session.commit()

    zh = await client.get("/api/search", params={"q": "水体"})
    assert [item["slug"] for item in zh.json()["projects"]] == ["water"]

    en = await client.get(
        "/api/search", params={"q": "Water", "locale": "en"}
    )
    assert [item["slug"] for item in en.json()["projects"]] == ["water"]

    cross = await client.get(
        "/api/search", params={"q": "水体", "locale": "en"}
    )
    assert cross.json()["projects"] == []


async def test_search_query_validation(client):
    empty = await client.get("/api/search", params={"q": "   "})
    assert empty.status_code == 200
    assert empty.json() == {"posts": [], "projects": [], "total": 0}

    missing = await client.get("/api/search")
    assert missing.status_code == 422

    too_long = await client.get("/api/search", params={"q": "a" * 101})
    assert too_long.status_code == 422


async def test_search_limits_each_group(client, db_session):
    db_session.add_all(
        [make_post(f"post-{i}", title=f"Searchable {i}") for i in range(11)]
    )
    db_session.add_all(
        [
            make_project(
                slug=f"project-{i}",
                title_zh=f"Searchable {i}",
                summary_zh="",
                content_md_zh="",
            )
            for i in range(11)
        ]
    )
    await db_session.commit()

    body = (
        await client.get("/api/search", params={"q": "Searchable"})
    ).json()
    assert len(body["posts"]) == 10
    assert len(body["projects"]) == 10
    assert body["total"] == 20


async def test_search_treats_like_wildcards_literally(client, db_session):
    db_session.add_all(
        [
            make_post("percent", title="100% done"),
            make_post("plain", title="plain"),
            make_post("underscore", title="a_b"),
            make_post("other", title="axb"),
        ]
    )
    await db_session.commit()

    percent = await client.get("/api/search", params={"q": "%"})
    assert [item["slug"] for item in percent.json()["posts"]] == ["percent"]

    underscore = await client.get("/api/search", params={"q": "_"})
    assert [item["slug"] for item in underscore.json()["posts"]] == [
        "underscore"
    ]


async def test_search_ranks_title_match_first(client, db_session):
    db_session.add_all(
        [
            make_post("content-only", title="其它", content_md="FastAPI 正文"),
            make_post("title-match", title="FastAPI", content_md="正文"),
        ]
    )
    await db_session.commit()

    body = (
        await client.get("/api/search", params={"q": "FastAPI"})
    ).json()
    assert [item["slug"] for item in body["posts"]] == [
        "title-match",
        "content-only",
    ]


async def test_search_projects_follow_featured_and_sort_order(client, db_session):
    db_session.add_all(
        [
            make_project(
                slug="normal-first",
                title_zh="检索",
                summary_zh="检索",
                content_md_zh="",
                featured=False,
                sort_order=1,
            ),
            make_project(
                slug="featured",
                title_zh="检索",
                summary_zh="检索",
                content_md_zh="",
                featured=True,
                sort_order=99,
            ),
            make_project(
                slug="normal-second",
                title_zh="检索",
                summary_zh="检索",
                content_md_zh="",
                featured=False,
                sort_order=2,
            ),
        ]
    )
    await db_session.commit()

    body = (
        await client.get("/api/search", params={"q": "检索"})
    ).json()
    assert [item["slug"] for item in body["projects"]] == [
        "featured",
        "normal-first",
        "normal-second",
    ]
```

- [ ] **步骤 2：运行测试确认失败**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_search.py -q
```

预期：全部失败，`/api/search` 返回 404。

- [ ] **步骤 3：创建响应 schema**

创建 `backend/app/schemas/search.py`：

```python
from pydantic import BaseModel

from app.schemas.post import PostListItem
from app.schemas.project import ProjectListItem


class SearchResponse(BaseModel):
    posts: list[PostListItem]
    projects: list[ProjectListItem]
    total: int
```

- [ ] **步骤 4：创建搜索 service**

创建 `backend/app/services/search.py`：

```python
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.post import Post
from app.models.project import Project

SEARCH_LIMIT = 10
_LIKE_ESCAPE = "\\"


def escape_like(value: str) -> str:
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


async def search_posts(db: AsyncSession, q: str) -> list[Post]:
    pattern = f"%{escape_like(q)}%"
    fields = [Post.title, Post.excerpt, Post.content_md]
    match = or_(*[field.ilike(pattern, escape=_LIKE_ESCAPE) for field in fields])
    score = func.greatest(*[func.similarity(field, q) for field in fields])

    result = await db.execute(
        select(Post)
        .where(Post.status == "published", match)
        .options(defer(Post.content_md))
        .order_by(
            score.desc(),
            Post.published_at.desc().nullslast(),
            Post.id.desc(),
        )
        .limit(SEARCH_LIMIT)
    )
    return list(result.scalars().unique())


async def search_projects(
    db: AsyncSession, q: str, locale: str
) -> list[Project]:
    pattern = f"%{escape_like(q)}%"
    fields = [
        getattr(Project, f"title_{locale}"),
        getattr(Project, f"summary_{locale}"),
        getattr(Project, f"content_md_{locale}"),
    ]
    match = or_(*[field.ilike(pattern, escape=_LIKE_ESCAPE) for field in fields])
    score = func.greatest(*[func.similarity(field, q) for field in fields])

    result = await db.execute(
        select(Project)
        .where(Project.status == "published", match)
        .order_by(
            score.desc(),
            Project.featured.desc(),
            Project.sort_order.asc(),
            Project.id.desc(),
        )
        .limit(SEARCH_LIMIT)
    )
    return list(result.scalars().all())


async def search_all(
    db: AsyncSession, *, q: str, locale: str
) -> tuple[list[Post], list[Project], int]:
    term = q.strip()
    if not term:
        return [], [], 0

    posts = await search_posts(db, term)
    projects = await search_projects(db, term, locale)
    return posts, projects, len(posts) + len(projects)
```

- [ ] **步骤 5：创建搜索路由并注册**

创建 `backend/app/api/public/search.py`：

```python
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.post import PostListItem
from app.schemas.project import ProjectListItem
from app.schemas.search import SearchResponse
from app.services.projects import localize_project
from app.services.search import search_all

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., max_length=100),
    locale: str = Query("zh", pattern="^(zh|en)$"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    posts, projects, total = await search_all(db, q=q, locale=locale)
    return SearchResponse(
        posts=[PostListItem.model_validate(post) for post in posts],
        projects=[
            ProjectListItem(**localize_project(project, locale))
            for project in projects
        ],
        total=total,
    )
```

修改 `backend/app/main.py`：

```python
from app.api.public import auth, posts, projects, search, site, tags
```

并在 `app.include_router(projects.router, prefix="/api")` 之后加入：

```python
app.include_router(search.router, prefix="/api")
```

- [ ] **步骤 6：运行测试确认通过**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest tests/test_search.py -q
```

预期：全部 PASS。

- [ ] **步骤 7：运行全量后端测试**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q
```

预期：原 69 条 + 新增全部 PASS。

- [ ] **步骤 8：Commit**

```bash
git add backend/app/schemas/search.py backend/app/services/search.py backend/app/api/public/search.py backend/app/main.py backend/tests/test_search.py
git commit -m "feat: add grouped post and project search API"
```

---

## 任务 3：先写前端 E2E 测试（红）

**文件：**
- 创建：`frontend/e2e/tags.spec.ts`
- 创建：`frontend/e2e/search.spec.ts`

- [ ] **步骤 1：创建标签 E2E**

创建 `frontend/e2e/tags.spec.ts`：

```ts
import {expect, test} from '@playwright/test';
import {loginAsAdmin} from './helpers';

test('admin can create, rename and delete a tag', async ({page}) => {
  const stamp = Date.now();
  const name = `E2E 标签 ${stamp}`;
  const slug = `e2e-tag-${stamp}`;
  const renamed = `E2E 改名 ${stamp}`;

  await loginAsAdmin(page);
  await page.getByRole('link', {name: '标签', exact: true}).click();
  await expect(page).toHaveURL(/\/zh\/admin\/tags$/);

  await page.getByLabel('名称').fill(name);
  await page.getByLabel('Slug').fill(slug);
  await page.getByRole('button', {name: '创建'}).click();

  const row = page.locator('li').filter({hasText: name});
  await expect(row).toBeVisible();

  await row.getByRole('button', {name: '编辑'}).click();
  await row.getByLabel('名称').fill(renamed);
  await row.getByRole('button', {name: '保存'}).click();

  const renamedRow = page.locator('li').filter({hasText: renamed});
  await expect(renamedRow).toBeVisible();

  page.once('dialog', (dialog) => dialog.accept());
  await renamedRow.getByRole('button', {name: '删除'}).click();
  await expect(renamedRow).toHaveCount(0);
});

test('post tag links open the tag page and unknown tags are 404', async ({
  page
}) => {
  await page.goto('/zh/posts');
  await page.getByRole('link', {name: /#后端/}).first().click();
  await expect(page).toHaveURL(/\/zh\/tags\/backend$/);
  await expect(
    page.getByRole('heading', {level: 1})
  ).toContainText('后端');
  await expect(
    page.getByRole('link', {name: '第一篇测试文章'})
  ).toBeVisible();

  const response = await page.goto('/zh/tags/no-such-tag');
  expect(response?.status()).toBe(404);
  await expect(
    page.getByRole('heading', {name: '页面不存在'})
  ).toBeVisible();
});
```

- [ ] **步骤 2：创建搜索 E2E**

创建 `frontend/e2e/search.spec.ts`：

```ts
import {expect, test} from '@playwright/test';

test('search page finds seeded posts and shows empty states', async ({
  page
}) => {
  await page.goto('/zh');
  await expect(
    page.getByRole('link', {name: '搜索', exact: true})
  ).toBeVisible();

  await page.goto('/zh/search');
  await expect(page.getByText('输入关键词开始搜索。')).toBeVisible();

  await page.getByLabel('搜索关键词').fill('第一篇');
  await page.getByRole('button', {name: '搜索'}).click();
  await expect(page).toHaveURL(/\/zh\/search\?q=/);
  await expect(
    page.getByRole('link', {name: '第一篇测试文章'})
  ).toBeVisible();

  await page.goto('/zh/search?q=zzzz-not-found');
  await expect(page.getByText('没有找到匹配的内容。')).toBeVisible();
});
```

- [ ] **步骤 3：运行 E2E 确认失败**

```bash
cd Z:/my_blog/frontend
npm run test:e2e -- e2e/tags.spec.ts e2e/search.spec.ts
```

预期：失败——后台没有「标签」导航与页面，公开站没有标签页、搜索页和搜索导航。**不要 commit 失败测试**，与后续任务一起提交。

---

## 任务 4：前端数据层与文案

**文件：**
- 修改：`frontend/src/lib/api.ts`
- 修改：`frontend/src/lib/admin-types.ts`
- 修改：`frontend/src/messages/zh.json`
- 修改：`frontend/src/messages/en.json`

- [ ] **步骤 1：扩展公开 API 客户端**

在 `frontend/src/lib/api.ts` 的 `Tag` 类型之后加入：

```ts
export type TagWithCount = Tag & {
  post_count: number;
};
```

在 `getPostOrNull` 之后加入：

```ts
export async function getTags(): Promise<TagWithCount[]> {
  return fetchApi<TagWithCount[]>('/api/tags');
}
```

在 `getSiteConfig` 之前加入：

```ts
export type SearchResponse = {
  posts: PostListItem[];
  projects: ProjectListItem[];
  total: number;
};

export async function search(params: {
  q: string;
  locale: ProjectLocale;
}): Promise<SearchResponse> {
  const query = new URLSearchParams({
    q: params.q,
    locale: params.locale
  });
  return fetchApi<SearchResponse>(`/api/search?${query.toString()}`);
}
```

- [ ] **步骤 2：扩展后台类型**

将 `frontend/src/lib/admin-types.ts` 的 `AdminTag` 替换为：

```ts
export type AdminTagRef = {
  id: number;
  name: string;
  slug: string;
};

export type AdminTag = AdminTagRef & {
  post_count: number;
};
```

同时把 `AdminPostListItem.tags` 的类型从 `AdminTag[]` 改为 `AdminTagRef[]`（后端文章接口返回轻量标签）。

- [ ] **步骤 3：添加中文文案**

修改 `frontend/src/messages/zh.json`：

在 `nav.posts` 之后加入 `"search": "搜索",`；在 `"projects"` 对象之前加入：

```json
"tags": {
  "title": "标签",
  "count": "共 {count} 篇文章",
  "empty": "该标签下暂无文章"
},
"search": {
  "title": "搜索",
  "label": "搜索关键词",
  "placeholder": "输入关键词…",
  "submit": "搜索",
  "prompt": "输入关键词开始搜索。",
  "empty": "没有找到匹配的内容。",
  "resultCount": "找到 {count} 条结果",
  "posts": "文章",
  "projects": "项目"
},
```

在 `admin.nav.media` 之后加入 `"tags": "标签",`；在 `admin.media` 对象之前加入：

```json
"tags": {
  "title": "标签管理",
  "name": "名称",
  "slug": "Slug",
  "create": "创建",
  "postCount": "{count} 篇文章",
  "edit": "编辑",
  "save": "保存",
  "saving": "保存中…",
  "cancel": "取消",
  "delete": "删除",
  "empty": "暂无标签",
  "createFailed": "创建失败，请稍后重试",
  "saveFailed": "保存失败，请稍后重试",
  "deleteFailed": "删除失败，请稍后重试",
  "conflict": "名称或 Slug 已存在",
  "invalid": "输入不合法，请检查名称与 Slug",
  "confirmDelete": "确定删除标签《{name}》？将影响 {count} 篇文章，文章不会被删除。"
},
```

- [ ] **步骤 4：添加英文文案**

修改 `frontend/src/messages/en.json`：

在 `nav.posts` 之后加入 `"search": "Search",`；在 `"projects"` 对象之前加入：

```json
"tags": {
  "title": "Tags",
  "count": "{count} posts",
  "empty": "No posts under this tag yet"
},
"search": {
  "title": "Search",
  "label": "Search keywords",
  "placeholder": "Type keywords…",
  "submit": "Search",
  "prompt": "Enter keywords to start searching.",
  "empty": "No matching content found.",
  "resultCount": "{count} results",
  "posts": "Posts",
  "projects": "Projects"
},
```

在 `admin.nav.media` 之后加入 `"tags": "Tags",`；在 `admin.media` 对象之前加入：

```json
"tags": {
  "title": "Tags",
  "name": "Name",
  "slug": "Slug",
  "create": "Create",
  "postCount": "{count} posts",
  "edit": "Edit",
  "save": "Save",
  "saving": "Saving…",
  "cancel": "Cancel",
  "delete": "Delete",
  "empty": "No tags yet",
  "createFailed": "Create failed. Please try again.",
  "saveFailed": "Save failed. Please try again.",
  "deleteFailed": "Delete failed. Please try again.",
  "conflict": "Name or slug already exists",
  "invalid": "Invalid input. Check the name and slug.",
  "confirmDelete": "Delete tag “{name}”? It affects {count} posts; posts will be kept."
},
```

- [ ] **步骤 5：类型检查**

```bash
cd Z:/my_blog/frontend
npx tsc --noEmit
```

预期：通过。

- [ ] **步骤 6：Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/lib/admin-types.ts frontend/src/messages/zh.json frontend/src/messages/en.json
git commit -m "feat: add tag and search API clients and copy"
```

---

## 任务 5：共用文章列表、标签 chips 与公开标签页

**文件：**
- 创建：`frontend/src/components/post-list.tsx`
- 修改：`frontend/src/components/post-card.tsx`
- 修改：`frontend/src/app/[locale]/(site)/posts/page.tsx`
- 创建：`frontend/src/app/[locale]/(site)/tags/[slug]/page.tsx`

- [ ] **步骤 1：创建共用列表组件**

创建 `frontend/src/components/post-list.tsx`：

```tsx
import {getTranslations} from 'next-intl/server';
import PostCard from '@/components/post-card';
import {Link} from '@/i18n/navigation';
import type {PostListItem} from '@/lib/api';

export default async function PostList({
  items,
  total,
  page,
  pageSize,
  locale,
  basePath = '/posts',
  emptyText
}: {
  items: PostListItem[];
  total: number;
  page: number;
  pageSize: number;
  locale: string;
  basePath?: string;
  emptyText: string;
}) {
  const t = await getTranslations('posts');
  const lastPage = Math.max(1, Math.ceil(total / pageSize));

  return (
    <>
      <div className="mt-8 grid gap-4">
        {items.length === 0 ? (
          <p className="text-muted">{emptyText}</p>
        ) : (
          items.map((post) => (
            <PostCard key={post.slug} post={post} locale={locale} />
          ))
        )}
      </div>

      <nav className="mt-8 flex gap-4 font-mono text-sm">
        {page > 1 ? (
          <Link
            href={`${basePath}?page=${page - 1}`}
            className="hover:text-accent"
          >
            ← {t('prev')}
          </Link>
        ) : null}
        {page < lastPage ? (
          <Link
            href={`${basePath}?page=${page + 1}`}
            className="hover:text-accent"
          >
            {t('next')} →
          </Link>
        ) : null}
      </nav>
    </>
  );
}
```

- [ ] **步骤 2：文章卡片标签改为链接**

修改 `frontend/src/components/post-card.tsx` 中标签渲染：

```tsx
      <div className="mt-4 flex flex-wrap gap-2 font-mono text-xs text-accent">
        {post.tags.map((tag) => (
          <Link
            key={tag.slug}
            href={`/tags/${tag.slug}`}
            className="hover:underline"
          >
            #{tag.name}
          </Link>
        ))}
      </div>
```

- [ ] **步骤 3：改写文章列表页**

将 `frontend/src/app/[locale]/(site)/posts/page.tsx` 全文替换为：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostList from '@/components/post-list';
import {Link} from '@/i18n/navigation';
import {getPosts, getTags} from '@/lib/api';

const PAGE_SIZE = 10;

export default async function PostsPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{page?: string | string[]}>;
}) {
  const {locale} = await params;
  const {page: pageParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('posts');
  const tTags = await getTranslations('tags');
  const rawPage = Array.isArray(pageParam) ? pageParam[0] : pageParam;
  const parsedPage = Number(rawPage);
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const [data, tags] = await Promise.all([
    getPosts({page, pageSize: PAGE_SIZE}),
    getTags()
  ]);
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
  if (page > lastPage) {
    notFound();
  }

  const visibleTags = tags.filter((tag) => tag.post_count > 0);

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      {visibleTags.length > 0 ? (
        <div
          aria-label={tTags('title')}
          className="mt-6 flex flex-wrap items-center gap-2 font-mono text-xs"
        >
          {visibleTags.map((tag) => (
            <Link
              key={tag.slug}
              href={`/tags/${tag.slug}`}
              className="rounded border border-border px-2 py-1 text-muted hover:border-accent hover:text-accent"
            >
              #{tag.name} <span className="text-accent">{tag.post_count}</span>
            </Link>
          ))}
        </div>
      ) : null}

      <PostList
        items={data.items}
        total={data.total}
        page={page}
        pageSize={PAGE_SIZE}
        emptyText={t('empty')}
        locale={locale}
      />
    </section>
  );
}
```


- [ ] **步骤 4：创建公开标签页**

创建 `frontend/src/app/[locale]/(site)/tags/[slug]/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import {notFound} from 'next/navigation';
import PostList from '@/components/post-list';
import {getPosts, getTags} from '@/lib/api';

const PAGE_SIZE = 10;

export default async function TagPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string; slug: string}>;
  searchParams: Promise<{page?: string | string[]}>;
}) {
  const {locale, slug} = await params;
  const {page: pageParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('tags');
  const rawPage = Array.isArray(pageParam) ? pageParam[0] : pageParam;
  const parsedPage = Number(rawPage);
  const page =
    Number.isSafeInteger(parsedPage) && parsedPage > 0 ? parsedPage : 1;

  const tags = await getTags();
  const tag = tags.find((item) => item.slug === slug);
  if (!tag) {
    notFound();
  }

  const data = await getPosts({page, pageSize: PAGE_SIZE, tag: slug});
  const lastPage = Math.max(1, Math.ceil(data.total / data.page_size));
  if (page > lastPage) {
    notFound();
  }

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">
        &gt; #{tag.name}_
      </h1>
      <p className="mt-2 font-mono text-xs text-muted">
        {t('count', {count: tag.post_count})}
      </p>

      <PostList
        items={data.items}
        total={data.total}
        page={page}
        pageSize={PAGE_SIZE}
        basePath={`/tags/${slug}`}
        emptyText={t('empty')}
        locale={locale}
      />
    </section>
  );
}
```

- [ ] **步骤 5：类型检查**

```bash
cd Z:/my_blog/frontend
npx tsc --noEmit
```

预期：通过。

- [ ] **步骤 6：Commit**

```bash
git add frontend/src/components/post-list.tsx frontend/src/components/post-card.tsx "frontend/src/app/[locale]/(site)/posts/page.tsx" "frontend/src/app/[locale]/(site)/tags/[slug]/page.tsx"
git commit -m "feat: add public tag pages and tag links"
```

---

## 任务 6：搜索页与页头入口

**文件：**
- 创建：`frontend/src/app/[locale]/(site)/search/page.tsx`
- 修改：`frontend/src/components/site-header.tsx`

- [ ] **步骤 1：创建搜索页**

创建 `frontend/src/app/[locale]/(site)/search/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import PostCard from '@/components/post-card';
import ProjectCard from '@/components/project-card';
import {search as searchApi} from '@/lib/api';

export default async function SearchPage({
  params,
  searchParams
}: {
  params: Promise<{locale: string}>;
  searchParams: Promise<{q?: string | string[]}>;
}) {
  const {locale} = await params;
  const {q: qParam} = await searchParams;
  setRequestLocale(locale);
  const t = await getTranslations('search');
  const rawQ = Array.isArray(qParam) ? qParam[0] : qParam;
  const q = (rawQ ?? '').trim().slice(0, 100);
  const projectLocale = locale === 'en' ? 'en' : 'zh';

  const data = q ? await searchApi({q, locale: projectLocale}) : null;

  return (
    <section className="mx-auto max-w-5xl px-4 py-12">
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>

      <form
        action={`/${locale}/search`}
        method="get"
        className="mt-6 flex flex-wrap gap-3"
      >
        <label htmlFor="q" className="sr-only">
          {t('label')}
        </label>
        <input
          id="q"
          name="q"
          defaultValue={q}
          maxLength={100}
          placeholder={t('placeholder')}
          className="w-full max-w-md rounded border border-border bg-surface px-3 py-2 font-mono text-sm sm:w-auto"
        />
        <button
          type="submit"
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black"
        >
          {t('submit')}
        </button>
      </form>

      {!data ? (
        <p className="mt-8 text-muted">{t('prompt')}</p>
      ) : data.total === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <div className="mt-8 grid gap-10">
          <p className="font-mono text-xs text-muted">
            {t('resultCount', {count: data.total})}
          </p>

          {data.posts.length > 0 ? (
            <section>
              <h2 className="font-mono text-lg text-accent">
                &gt; {t('posts')}
              </h2>
              <div className="mt-4 grid gap-4">
                {data.posts.map((post) => (
                  <PostCard
                    key={post.slug}
                    post={post}
                    locale={locale}
                    headingLevel={3}
                  />
                ))}
              </div>
            </section>
          ) : null}

          {data.projects.length > 0 ? (
            <section>
              <h2 className="font-mono text-lg text-accent">
                &gt; {t('projects')}
              </h2>
              <div className="mt-4 grid gap-4 sm:grid-cols-2">
                {data.projects.map((project) => (
                  <ProjectCard
                    key={project.slug}
                    project={project}
                    locale={locale}
                  />
                ))}
              </div>
            </section>
          ) : null}
        </div>
      )}
    </section>
  );
}
```

- [ ] **步骤 2：页头加入搜索入口**

修改 `frontend/src/components/site-header.tsx`，在文章链接之后加入：

```tsx
          <Link href="/search" className="hover:text-foreground">
            {t('search')}
          </Link>
```

- [ ] **步骤 3：类型检查**

```bash
cd Z:/my_blog/frontend
npx tsc --noEmit
```

预期：通过。

- [ ] **步骤 4：Commit**

```bash
git add "frontend/src/app/[locale]/(site)/search/page.tsx" frontend/src/components/site-header.tsx
git commit -m "feat: add site search page and header link"
```

---

## 任务 7：后台标签管理页

**文件：**
- 创建：`frontend/src/app/[locale]/admin/(protected)/tags/page.tsx`
- 创建：`frontend/src/components/admin/tag-manager.tsx`
- 修改：`frontend/src/app/[locale]/admin/(protected)/layout.tsx`

- [ ] **步骤 1：创建后台标签页**

创建 `frontend/src/app/[locale]/admin/(protected)/tags/page.tsx`：

```tsx
import {getTranslations, setRequestLocale} from 'next-intl/server';
import TagManager from '@/components/admin/tag-manager';
import {getAdminTags} from '@/lib/admin-api';

export default async function AdminTagsPage({
  params
}: {
  params: Promise<{locale: string}>;
}) {
  const {locale} = await params;
  setRequestLocale(locale);
  const t = await getTranslations('admin.tags');
  const tags = await getAdminTags();

  return (
    <section>
      <h1 className="font-mono text-2xl text-accent">&gt; {t('title')}_</h1>
      <TagManager tags={tags} />
    </section>
  );
}
```

- [ ] **步骤 2：创建标签管理客户端组件**

创建 `frontend/src/components/admin/tag-manager.tsx`：

```tsx
'use client';

import {useLocale, useTranslations} from 'next-intl';
import {useRouter} from 'next/navigation';
import {useState} from 'react';
import type {AdminTag} from '@/lib/admin-types';

function sortTags(tags: AdminTag[]) {
  return [...tags].sort((a, b) => a.name.localeCompare(b.name));
}

export default function TagManager({tags: initialTags}: {tags: AdminTag[]}) {
  const t = useTranslations('admin.tags');
  const locale = useLocale();
  const router = useRouter();
  const [tags, setTags] = useState(() => sortTags(initialTags));
  const [newName, setNewName] = useState('');
  const [newSlug, setNewSlug] = useState('');
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editName, setEditName] = useState('');
  const [editSlug, setEditSlug] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function handleFailure(status: number, fallback: string) {
    if (status === 401) {
      router.replace(`/${locale}/admin/login`);
      return;
    }
    if (status === 409) {
      setError(t('conflict'));
      return;
    }
    if (status === 422) {
      setError(t('invalid'));
      return;
    }
    setError(fallback);
  }

  async function create(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const name = newName.trim();
    const slug = newSlug.trim();
    if (!name || !slug) return;

    setPending(true);
    setError(null);
    try {
      const response = await fetch('/api/admin/tags', {
        method: 'POST',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({name, slug})
      });
      if (!response.ok) {
        handleFailure(response.status, t('createFailed'));
        return;
      }
      const tag = (await response.json()) as AdminTag;
      setTags((current) => sortTags([...current, tag]));
      setNewName('');
      setNewSlug('');
    } catch {
      setError(t('createFailed'));
    } finally {
      setPending(false);
    }
  }

  function startEdit(tag: AdminTag) {
    setEditingId(tag.id);
    setEditName(tag.name);
    setEditSlug(tag.slug);
    setError(null);
  }

  async function save(id: number) {
    const name = editName.trim();
    const slug = editSlug.trim();
    if (!name || !slug) return;

    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/tags/${id}`, {
        method: 'PATCH',
        headers: {'content-type': 'application/json'},
        body: JSON.stringify({name, slug})
      });
      if (!response.ok) {
        handleFailure(response.status, t('saveFailed'));
        return;
      }
      const tag = (await response.json()) as AdminTag;
      setTags((current) =>
        sortTags(current.map((item) => (item.id === id ? tag : item)))
      );
      setEditingId(null);
    } catch {
      setError(t('saveFailed'));
    } finally {
      setPending(false);
    }
  }

  async function remove(tag: AdminTag) {
    if (
      !window.confirm(
        t('confirmDelete', {name: tag.name, count: tag.post_count})
      )
    ) {
      return;
    }

    setPending(true);
    setError(null);
    try {
      const response = await fetch(`/api/admin/tags/${tag.id}`, {
        method: 'DELETE'
      });
      if (response.status === 401) {
        router.replace(`/${locale}/admin/login`);
        return;
      }
      if (!response.ok) {
        handleFailure(response.status, t('deleteFailed'));
        return;
      }
      setTags((current) => current.filter((item) => item.id !== tag.id));
    } catch {
      setError(t('deleteFailed'));
    } finally {
      setPending(false);
    }
  }

  return (
    <div>
      <form
        onSubmit={create}
        className="mt-6 flex flex-wrap items-end gap-3 font-mono text-xs"
      >
        <label className="grid gap-1">
          <span className="text-muted">{t('name')}</span>
          <input
            value={newName}
            onChange={(event) => setNewName(event.target.value)}
            required
            className="rounded border border-border bg-surface px-2 py-1"
          />
        </label>
        <label className="grid gap-1">
          <span className="text-muted">{t('slug')}</span>
          <input
            value={newSlug}
            onChange={(event) => setNewSlug(event.target.value)}
            required
            className="rounded border border-border bg-surface px-2 py-1"
          />
        </label>
        <button
          type="submit"
          disabled={pending || !newName.trim() || !newSlug.trim()}
          className="rounded bg-accent px-4 py-2 font-mono text-sm font-semibold text-black disabled:opacity-60"
        >
          {t('create')}
        </button>
      </form>

      {error ? (
        <p role="alert" className="mt-4 font-mono text-xs text-red-400">
          {error}
        </p>
      ) : null}

      {tags.length === 0 ? (
        <p className="mt-8 text-muted">{t('empty')}</p>
      ) : (
        <ul className="mt-8 grid gap-3">
          {tags.map((tag) => (
            <li
              key={tag.id}
              data-testid={`admin-tag-${tag.slug}`}
              className="rounded border border-border bg-surface p-4"
            >
              {editingId === tag.id ? (
                <form
                  onSubmit={(event) => {
                    event.preventDefault();
                    void save(tag.id);
                  }}
                  className="flex flex-wrap items-end gap-3 font-mono text-xs"
                >
                  <label className="grid gap-1">
                    <span className="text-muted">{t('name')}</span>
                    <input
                      value={editName}
                      onChange={(event) => setEditName(event.target.value)}
                      required
                      className="rounded border border-border bg-background px-2 py-1"
                    />
                  </label>
                  <label className="grid gap-1">
                    <span className="text-muted">{t('slug')}</span>
                    <input
                      value={editSlug}
                      onChange={(event) => setEditSlug(event.target.value)}
                      required
                      className="rounded border border-border bg-background px-2 py-1"
                    />
                  </label>
                  <button
                    type="submit"
                    disabled={pending}
                    className="rounded bg-accent px-3 py-1 font-semibold text-black disabled:opacity-60"
                  >
                    {pending ? t('saving') : t('save')}
                  </button>
                  <button
                    type="button"
                    onClick={() => setEditingId(null)}
                    className="rounded border border-border px-3 py-1 hover:border-accent"
                  >
                    {t('cancel')}
                  </button>
                </form>
              ) : (
                <div className="flex flex-wrap items-center justify-between gap-3 font-mono text-sm">
                  <div className="flex flex-wrap items-baseline gap-2">
                    <span className="text-accent">#{tag.name}</span>
                    <span className="text-xs text-muted">/{tag.slug}</span>
                  </div>
                  <span className="text-xs text-muted">
                    {t('postCount', {count: tag.post_count})}
                  </span>
                  <div className="flex gap-3 text-xs">
                    <button
                      type="button"
                      onClick={() => startEdit(tag)}
                      className="hover:text-accent"
                    >
                      {t('edit')}
                    </button>
                    <button
                      type="button"
                      onClick={() => void remove(tag)}
                      disabled={pending}
                      className="text-red-400 hover:underline disabled:opacity-60"
                    >
                      {t('delete')}
                    </button>
                  </div>
                </div>
              )}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
```

- [ ] **步骤 3：后台导航加入标签**

修改 `frontend/src/app/[locale]/admin/(protected)/layout.tsx`，在项目链接之后加入：

```tsx
            <Link href="/admin/tags" className="hover:text-accent">
              {t('tags')}
            </Link>
```

- [ ] **步骤 4：类型检查**

```bash
cd Z:/my_blog/frontend
npx tsc --noEmit
```

预期：通过。

- [ ] **步骤 5：Commit（连同任务 3 的 E2E 测试）**

```bash
git add "frontend/src/app/[locale]/admin/(protected)/tags/page.tsx" frontend/src/components/admin/tag-manager.tsx "frontend/src/app/[locale]/admin/(protected)/layout.tsx" frontend/e2e/tags.spec.ts frontend/e2e/search.spec.ts
git commit -m "feat: add admin tag management and e2e coverage"
```

---

## 任务 8：全量验证与文档

**文件：**
- 修改：`README.md`
- 修改：`HANDOFF.md`

- [ ] **步骤 1：运行新增 E2E**

```bash
cd Z:/my_blog/frontend
npm run test:e2e -- e2e/tags.spec.ts e2e/search.spec.ts
```

预期：3 条测试全部 PASS（标签 2 条 + 搜索 1 条）。

- [ ] **步骤 2：运行全量 E2E**

```bash
cd Z:/my_blog/frontend
npm run test:e2e
```

预期：9 条全部 PASS（原 6 条 + 新增 3 条）。

- [ ] **步骤 3：生产构建**

```bash
cd Z:/my_blog/frontend
npm run build
```

预期：成功，无 TypeScript/ESLint 错误。

- [ ] **步骤 4：后端全量测试**

```bash
cd Z:/my_blog/backend
"venv/Scripts/python.exe" -m pytest -q
```

预期：83 passed（原 69 条 + 标签 6 条 + 搜索 8 条）。

- [ ] **步骤 5：手工冒烟**

启动前后端后检查：

1. `/zh/posts` 显示标签 chips；点击进入 `/zh/tags/backend`。
2. 文章卡片 `#后端` 可点击。
3. `/zh/search?q=第一篇` 显示文章分组；`/zh/search?q=zzzz` 显示空状态。
4. `/zh/admin/tags` 可创建、改名、删除标签；删除后对应文章仍可访问。
5. `/en/search` 与 `/en/tags/backend` 文案正常。

- [ ] **步骤 6：更新 README**

在 `README.md` 的功能概述中补充标签管理与站内搜索；把测试基线从「69 passed」「6 passed」更新为「83 passed」「9 passed」；在「后台管理」一节补充标签管理说明。

- [ ] **步骤 7：更新 HANDOFF**

把「当前状态」更新为 3B 完成；在「已完成内容」加入标签管理、标签页、搜索；在「接下来要做什么」移除 3B，保留下一步 3C 评论；在「常用命令」无需改动。

- [ ] **步骤 8：Commit 文档**

```bash
git add README.md HANDOFF.md
git commit -m "docs: update feature and test baselines for tags and search"
```

- [ ] **步骤 9：最终检查工作树**

```bash
git status --short
git log --oneline -6
```

预期：工作树干净，提交历史包含规格、七个功能/测试提交与文档提交。

---

## 执行交接

计划完成后：

1. 先跑后端全量测试与前端构建，确认基线。
2. 用 `subagent-driven-development` 执行：每个任务一个实现子代理，随后进行规格审查与代码质量审查。
3. 所有任务完成后合并到 `master`，再按 HANDOFF 第 6 节用 bundle 更新线上服务器（3B 无迁移、无新依赖，只需 build + restart）。
