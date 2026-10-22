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
