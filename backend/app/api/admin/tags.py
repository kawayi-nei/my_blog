from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.tag import Tag
from app.schemas.admin_tag import AdminTagCreate, AdminTagOut, AdminTagUpdate
from app.services.admin_tags import (
    create_admin_tag,
    delete_admin_tag,
    list_admin_tags,
    update_admin_tag,
)

router = APIRouter(prefix="/tags", tags=["admin-tags"])


def _tag_out(tag: Tag, post_count: int) -> AdminTagOut:
    return AdminTagOut(
        id=tag.id, name=tag.name, slug=tag.slug, post_count=post_count
    )


@router.get("", response_model=list[AdminTagOut])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[AdminTagOut]:
    rows = await list_admin_tags(db)
    return [_tag_out(tag, count) for tag, count in rows]


@router.post("", response_model=AdminTagOut, status_code=201)
async def create_tag(
    payload: AdminTagCreate, db: AsyncSession = Depends(get_db)
) -> AdminTagOut:
    tag = await create_admin_tag(db, payload)
    return _tag_out(tag, 0)


@router.patch("/{tag_id}", response_model=AdminTagOut)
async def update_tag(
    tag_id: int, payload: AdminTagUpdate, db: AsyncSession = Depends(get_db)
) -> AdminTagOut:
    tag, post_count = await update_admin_tag(db, tag_id, payload)
    return _tag_out(tag, post_count)


@router.delete("/{tag_id}", status_code=204)
async def delete_tag(
    tag_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    await delete_admin_tag(db, tag_id)
