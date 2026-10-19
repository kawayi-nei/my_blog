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
