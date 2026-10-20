from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.post import Post
from app.models.tag import Tag
from app.schemas.admin_post import AdminPostCreate, AdminPostUpdate


async def list_admin_posts(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    q: str | None = None,
) -> tuple[list[Post], int]:
    filters = []
    if status:
        filters.append(Post.status == status)
    if q:
        pattern = f"%{q}%"
        filters.append(or_(Post.title.ilike(pattern), Post.excerpt.ilike(pattern)))

    total = (
        await db.scalar(select(func.count()).select_from(Post).where(*filters)) or 0
    )
    result = await db.execute(
        select(Post)
        .where(*filters)
        .options(defer(Post.content_md))
        .order_by(Post.updated_at.desc(), Post.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().unique()), total


async def get_admin_post(db: AsyncSession, post_id: int) -> Post | None:
    result = await db.execute(select(Post).where(Post.id == post_id))
    return result.scalar_one_or_none()


async def _load_tags(db: AsyncSession, tag_ids: list[int]) -> list[Tag]:
    if not tag_ids:
        return []
    result = await db.execute(select(Tag).where(Tag.id.in_(tag_ids)))
    tags = list(result.scalars().all())
    if len(tags) != len(set(tag_ids)):
        raise HTTPException(status_code=422, detail="标签不存在")
    return tags


async def _ensure_slug_available(
    db: AsyncSession, slug: str, *, exclude_id: int | None = None
) -> None:
    query = select(Post.id).where(Post.slug == slug)
    if exclude_id is not None:
        query = query.where(Post.id != exclude_id)
    if await db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail="slug 已存在")


async def create_admin_post(db: AsyncSession, data: AdminPostCreate) -> Post:
    await _ensure_slug_available(db, data.slug)
    tags = await _load_tags(db, data.tag_ids)
    now = datetime.now(timezone.utc)
    post = Post(
        slug=data.slug,
        title=data.title,
        excerpt=data.excerpt,
        content_md=data.content_md,
        language=data.language,
        status=data.status,
        published_at=now if data.status == "published" else None,
        tags=tags,
    )
    db.add(post)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug 已存在")
    await db.refresh(post)
    return post


async def update_admin_post(
    db: AsyncSession, post_id: int, data: AdminPostUpdate
) -> Post:
    post = await get_admin_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")

    changes = data.model_dump(exclude_unset=True)
    tag_ids = changes.pop("tag_ids", None)
    changes = {key: value for key, value in changes.items() if value is not None}

    new_slug = changes.get("slug")
    if new_slug is not None and new_slug != post.slug:
        await _ensure_slug_available(db, new_slug, exclude_id=post.id)

    if changes.get("status") == "published" and post.published_at is None:
        post.published_at = datetime.now(timezone.utc)

    for field, value in changes.items():
        setattr(post, field, value)

    if tag_ids is not None:
        post.tags = await _load_tags(db, tag_ids)

    post.updated_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug 已存在")
    await db.refresh(post)
    return post


async def delete_admin_post(db: AsyncSession, post_id: int) -> None:
    post = await get_admin_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    await db.delete(post)
    await db.commit()
