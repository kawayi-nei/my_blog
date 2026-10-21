async def test_create_project_and_public_visibility(admin_client, client):
    response = await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "my-project",
            "title_zh": "我的项目",
            "title_en": "My project",
            "summary_zh": "中文摘要",
            "summary_en": "English summary",
            "content_md_zh": "# 中文",
            "content_md_en": "# English",
            "tech_stack": [" React ", "React", "", "FastAPI"],
            "status": "published",
            "featured": True,
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["tech_stack"] == ["React", "FastAPI"]
    assert body["featured"] is True

    public = await client.get("/api/projects/my-project")
    assert public.status_code == 200
    assert public.json()["title"] == "我的项目"


async def test_draft_is_not_public(admin_client, client):
    created = await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "draft-project",
            "title_zh": "草稿",
            "title_en": "Draft",
            "status": "draft",
        },
    )
    assert created.status_code == 201
    assert (await client.get("/api/projects/draft-project")).status_code == 404


async def test_admin_list_filters(admin_client):
    await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "alpha",
            "title_zh": "Alpha 项目",
            "title_en": "Alpha",
            "status": "draft",
        },
    )
    await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "beta",
            "title_zh": "Beta 项目",
            "title_en": "Beta",
            "status": "published",
        },
    )

    drafts = await admin_client.get("/api/admin/projects?status=draft")
    assert [item["slug"] for item in drafts.json()["items"]] == ["alpha"]

    searched = await admin_client.get("/api/admin/projects?q=Beta")
    assert [item["slug"] for item in searched.json()["items"]] == ["beta"]


async def test_update_and_clear_nullable_fields(admin_client):
    created = await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "update-me",
            "title_zh": "更新前",
            "title_en": "Before",
            "summary_zh": "",
            "summary_en": "",
            "cover_url": "/uploads/a.png",
            "repo_url": "https://example.com/repo",
            "status": "draft",
        },
    )
    project_id = created.json()["id"]

    updated = await admin_client.patch(
        f"/api/admin/projects/{project_id}",
        json={
            "title_zh": "更新后",
            "cover_url": None,
            "repo_url": None,
            "status": "published",
        },
    )
    assert updated.status_code == 200
    body = updated.json()
    assert body["title_zh"] == "更新后"
    assert body["cover_url"] is None
    assert body["repo_url"] is None
    assert body["status"] == "published"


async def test_slug_conflict(admin_client):
    payload = {
        "slug": "taken",
        "title_zh": "一",
        "title_en": "One",
    }
    assert (await admin_client.post("/api/admin/projects", json=payload)).status_code == 201

    conflict = await admin_client.post(
        "/api/admin/projects",
        json={"slug": "taken", "title_zh": "二", "title_en": "Two"},
    )
    assert conflict.status_code == 409


async def test_invalid_tech_stack_and_dates(admin_client):
    too_many = await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "too-many",
            "title_zh": "多",
            "title_en": "Many",
            "tech_stack": [f"tech-{index}" for index in range(21)],
        },
    )
    assert too_many.status_code == 422

    bad_dates = await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "bad-dates",
            "title_zh": "日期",
            "title_en": "Dates",
            "started_on": "2026-05-01",
            "ended_on": "2026-04-01",
        },
    )
    assert bad_dates.status_code == 422


async def test_delete_project(admin_client):
    created = await admin_client.post(
        "/api/admin/projects",
        json={
            "slug": "delete-me",
            "title_zh": "删除",
            "title_en": "Delete",
        },
    )
    project_id = created.json()["id"]

    deleted = await admin_client.delete(f"/api/admin/projects/{project_id}")
    assert deleted.status_code == 204
    assert (await admin_client.get(f"/api/admin/projects/{project_id}")).status_code == 404
