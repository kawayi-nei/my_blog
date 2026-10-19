import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import selectinload

from app.models.post import Post, post_tags
from app.models.tag import Tag


async def test_post_tag_many_to_many(db_session):
    tag = Tag(name="后端", slug="backend")
    post = Post(slug="hello", title="Hello", content_md="x", tags=[tag])
    db_session.add(post)
    await db_session.commit()

    result = await db_session.execute(
        select(Post).where(Post.slug == "hello").options(selectinload(Post.tags))
    )
    loaded = result.scalar_one()
    assert [t.slug for t in loaded.tags] == ["backend"]

    result = await db_session.execute(
        select(Tag).where(Tag.slug == "backend").options(selectinload(Tag.posts))
    )
    assert [p.slug for p in result.scalar_one().posts] == ["hello"]


async def test_defaults(db_session):
    post = Post(slug="defaults", title="Defaults", content_md="x")
    db_session.add(post)
    await db_session.commit()
    await db_session.refresh(post)
    assert post.language == "zh"
    assert post.status == "draft"
    assert post.excerpt == ""
    assert post.view_count == 0


async def test_language_check(db_session):
    db_session.add(
        Post(slug="bad-lang", title="Bad", content_md="x", language="fr")
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_status_check(db_session):
    db_session.add(
        Post(slug="bad-status", title="Bad", content_md="x", status="archived")
    )
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_slug_format_check(db_session):
    db_session.add(Post(slug="Bad Slug", title="Bad", content_md="x"))
    with pytest.raises(IntegrityError):
        await db_session.commit()
    await db_session.rollback()


async def test_delete_post_cascades_post_tags(db_session):
    tag = Tag(name="后端", slug="backend")
    post = Post(slug="cascade", title="Cascade", content_md="x", tags=[tag])
    db_session.add(post)
    await db_session.commit()
    post_id = post.id

    await db_session.delete(post)
    await db_session.commit()

    count = await db_session.scalar(
        select(func.count()).select_from(post_tags).where(post_tags.c.post_id == post_id)
    )
    assert count == 0
