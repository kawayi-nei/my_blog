from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.media import MediaListResponse, MediaOut
from app.services.media import delete_media, list_media

router = APIRouter(prefix="/media", tags=["admin-media"])


@router.get("", response_model=MediaListResponse)
async def list_media_items(
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(24, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> MediaListResponse:
    items, total = await list_media(db, page=page, page_size=page_size)
    return MediaListResponse(
        items=[
            MediaOut(
                id=item.id,
                url=f"/uploads/{item.filename}",
                filename=item.filename,
                original_name=item.original_name,
                mime=item.mime,
                size_bytes=item.size_bytes,
                created_at=item.created_at,
            )
            for item in items
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.delete("/{media_id}", status_code=204)
async def delete_media_item(
    media_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    await delete_media(db, media_id)
