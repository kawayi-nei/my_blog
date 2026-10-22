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


async def test_admin_post_with_tag_serializes_without_post_count(admin_client):
    tag = (
        await admin_client.post(
            "/api/admin/tags", json={"name": "后端", "slug": "backend"}
        )
    ).json()

    created = await admin_client.post(
        "/api/admin/posts",
        json={
            "slug": "tagged-post",
            "title": "带标签文章",
            "content_md": "x",
            "status": "published",
            "tag_ids": [tag["id"]],
        },
    )
    assert created.status_code == 201
    assert created.json()["tags"] == [
        {"id": tag["id"], "name": "后端", "slug": "backend"}
    ]

    listed = await admin_client.get("/api/admin/posts")
    assert listed.status_code == 200
    item = next(
        item for item in listed.json()["items"] if item["slug"] == "tagged-post"
    )
    assert item["tags"] == [
        {"id": tag["id"], "name": "后端", "slug": "backend"}
    ]

    detail = await admin_client.get(f"/api/admin/posts/{created.json()['id']}")
    assert detail.status_code == 200
    assert detail.json()["tags"] == [
        {"id": tag["id"], "name": "后端", "slug": "backend"}
    ]
