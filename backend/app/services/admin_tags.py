from fastapi import HTTPException
from sqlalchemy import delete as sql_delete
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.post import Post, post_tags
from app.models.tag import Tag
from app.schemas.admin_tag import AdminTagCreate, AdminTagUpdate


async def list_admin_tags(db: AsyncSession) -> list[tuple[Tag, int]]:
    result = await db.execute(
        select(Tag, func.count(Post.id))
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .outerjoin(Post, Post.id == post_tags.c.post_id)
        .group_by(Tag.id)
        .order_by(Tag.name.asc(), Tag.id.asc())
    )
    return [(tag, count) for tag, count in result.all()]


async def _tag_post_count(db: AsyncSession, tag_id: int) -> int:
    return (
        await db.scalar(
            select(func.count())
            .select_from(post_tags)
            .where(post_tags.c.tag_id == tag_id)
        )
        or 0
    )


async def _ensure_available(
    db: AsyncSession,
    *,
    name: str | None,
    slug: str | None,
    exclude_id: int,
) -> None:
    conditions = []
    if name is not None:
        conditions.append(Tag.name == name)
    if slug is not None:
        conditions.append(Tag.slug == slug)
    if not conditions:
        return

    existing = await db.scalar(
        select(Tag.id).where(or_(*conditions), Tag.id != exclude_id)
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")


async def create_admin_tag(db: AsyncSession, data: AdminTagCreate) -> Tag:
    existing = await db.scalar(
        select(Tag.id).where(or_(Tag.name == data.name, Tag.slug == data.slug))
    )
    if existing is not None:
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")

    tag = Tag(name=data.name, slug=data.slug)
    db.add(tag)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")
    await db.refresh(tag)
    return tag


async def update_admin_tag(
    db: AsyncSession, tag_id: int, data: AdminTagUpdate
) -> tuple[Tag, int]:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")

    await _ensure_available(
        db, name=data.name, slug=data.slug, exclude_id=tag_id
    )

    if data.name is not None:
        tag.name = data.name
    if data.slug is not None:
        tag.slug = data.slug

    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="标签名称或 slug 已存在")
    await db.refresh(tag)
    return tag, await _tag_post_count(db, tag_id)


async def delete_admin_tag(db: AsyncSession, tag_id: int) -> None:
    tag = await db.get(Tag, tag_id)
    if tag is None:
        raise HTTPException(status_code=404, detail="标签不存在")

    await db.execute(sql_delete(Tag).where(Tag.id == tag_id))
    await db.commit()
