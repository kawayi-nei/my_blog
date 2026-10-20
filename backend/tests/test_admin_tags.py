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
