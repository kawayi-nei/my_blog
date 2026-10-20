from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin_tag import AdminTagCreate, AdminTagOut
from app.services.admin_tags import create_admin_tag, list_admin_tags

router = APIRouter(prefix="/tags", tags=["admin-tags"])


@router.get("", response_model=list[AdminTagOut])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[AdminTagOut]:
    tags = await list_admin_tags(db)
    return [AdminTagOut.model_validate(tag) for tag in tags]


@router.post("", response_model=AdminTagOut, status_code=201)
async def create_tag(
    payload: AdminTagCreate, db: AsyncSession = Depends(get_db)
) -> AdminTagOut:
    tag = await create_admin_tag(db, payload)
    return AdminTagOut.model_validate(tag)
