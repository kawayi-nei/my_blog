from datetime import date

from app.models.project import Project


def make_project(**overrides) -> Project:
    values = {
        "slug": "demo-project",
        "title_zh": "示例项目",
        "title_en": "Demo project",
        "summary_zh": "中文摘要",
        "summary_en": "English summary",
        "content_md_zh": "# 中文正文",
        "content_md_en": "# English body",
        "tech_stack": ["PyTorch"],
        "status": "published",
        "featured": True,
        "sort_order": 0,
        "started_on": date(2026, 1, 1),
    }
    values.update(overrides)
    return Project(**values)


async def test_public_list_only_published(client, db_session):
    db_session.add_all(
        [
            make_project(slug="published", title_zh="已发布", title_en="Published"),
            make_project(
                slug="draft",
                title_zh="草稿",
                title_en="Draft",
                status="draft",
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/projects")
    assert response.status_code == 200
    assert [item["slug"] for item in response.json()] == ["published"]


async def test_public_detail_and_draft_404(client, db_session):
    db_session.add_all(
        [
            make_project(slug="visible"),
            make_project(slug="hidden", status="draft"),
        ]
    )
    await db_session.commit()

    visible = await client.get("/api/projects/visible")
    assert visible.status_code == 200
    assert visible.json()["content_md"] == "# 中文正文"

    hidden = await client.get("/api/projects/hidden")
    assert hidden.status_code == 404


async def test_featured_filter(client, db_session):
    db_session.add_all(
        [
            make_project(slug="featured", featured=True),
            make_project(slug="normal", featured=False),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/projects?featured=true")
    assert [item["slug"] for item in response.json()] == ["featured"]

    all_items = await client.get("/api/projects")
    assert len(all_items.json()) == 2


async def test_public_ordering(client, db_session):
    db_session.add_all(
        [
            make_project(
                slug="later",
                featured=False,
                sort_order=2,
                started_on=date(2026, 3, 1),
            ),
            make_project(
                slug="featured",
                featured=True,
                sort_order=99,
                started_on=date(2025, 1, 1),
            ),
            make_project(
                slug="first",
                featured=False,
                sort_order=1,
                started_on=date(2026, 2, 1),
            ),
        ]
    )
    await db_session.commit()

    response = await client.get("/api/projects")
    assert [item["slug"] for item in response.json()] == [
        "featured",
        "first",
        "later",
    ]


async def test_localization_fallback(client, db_session):
    db_session.add(
        make_project(
            slug="fallback",
            summary_en="",
            content_md_en="",
            title_en="English title",
        )
    )
    await db_session.commit()

    response = await client.get("/api/projects/fallback?locale=en")
    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "English title"
    assert body["summary"] == "中文摘要"
    assert body["content_md"] == "# 中文正文"


async def test_localization_uses_requested_language(client, db_session):
    db_session.add(make_project(slug="localized"))
    await db_session.commit()

    en = await client.get("/api/projects/localized?locale=en")
    assert en.json()["title"] == "Demo project"
    assert en.json()["summary"] == "English summary"

    zh = await client.get("/api/projects/localized?locale=zh")
    assert zh.json()["title"] == "示例项目"
    assert zh.json()["summary"] == "中文摘要"


async def test_list_item_has_no_content(client, db_session):
    db_session.add(make_project(slug="list-shape"))
    await db_session.commit()

    response = await client.get("/api/projects")
    item = response.json()[0]
    assert "content_md" not in item
    assert item["tech_stack"] == ["PyTorch"]
