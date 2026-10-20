from fastapi import HTTPException
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.tag import Tag
from app.schemas.admin_tag import AdminTagCreate


async def list_admin_tags(db: AsyncSession) -> list[Tag]:
    result = await db.execute(select(Tag).order_by(Tag.name.asc(), Tag.id.asc()))
    return list(result.scalars().all())


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
