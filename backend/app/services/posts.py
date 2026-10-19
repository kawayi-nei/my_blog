from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post
from app.models.tag import Tag


async def list_published_posts(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    tag: str | None = None,
    language: str | None = None,
) -> tuple[list[Post], int]:
    filters = [Post.status == "published"]
    if tag:
        filters.append(Post.tags.any(Tag.slug == tag))
    if language:
        filters.append(Post.language == language)

    total = (
        await db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    )
    result = await db.execute(
        select(Post)
        .where(*filters)
        .order_by(Post.published_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique()), total


async def get_published_post(db: AsyncSession, slug: str) -> Post | None:
    result = await db.execute(
        select(Post).where(Post.slug == slug, Post.status == "published")
    )
    return result.scalar_one_or_none()
