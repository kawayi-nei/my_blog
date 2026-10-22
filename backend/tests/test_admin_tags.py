from datetime import datetime, timezone

from sqlalchemy import func, select

from app.core.config import get_settings
from app.models.post import Post, post_tags
from app.models.tag import Tag


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
