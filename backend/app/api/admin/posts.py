from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin_post import (
    AdminPostCreate,
    AdminPostDetail,
    AdminPostListItem,
    AdminPostListResponse,
    AdminPostUpdate,
)
from app.services.admin_posts import (
    create_admin_post,
    delete_admin_post,
    get_admin_post,
    list_admin_posts,
    update_admin_post,
)

router = APIRouter(prefix="/posts", tags=["admin-posts"])


@router.get("", response_model=AdminPostListResponse)
async def list_posts(
    status: str | None = Query(None, pattern="^(draft|published)$"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> AdminPostListResponse:
    query = q.strip() if q else None
    posts, total = await list_admin_posts(
        db,
        page=page,
        page_size=page_size,
        status=status,
        q=query or None,
    )
    return AdminPostListResponse(
        items=[AdminPostListItem.model_validate(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AdminPostDetail, status_code=201)
async def create_post(
    payload: AdminPostCreate, db: AsyncSession = Depends(get_db)
) -> AdminPostDetail:
    post = await create_admin_post(db, payload)
    return AdminPostDetail.model_validate(post)


@router.get("/{post_id}", response_model=AdminPostDetail)
async def get_post(
    post_id: int, db: AsyncSession = Depends(get_db)
) -> AdminPostDetail:
    post = await get_admin_post(db, post_id)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return AdminPostDetail.model_validate(post)


@router.patch("/{post_id}", response_model=AdminPostDetail)
async def update_post(
    post_id: int,
    payload: AdminPostUpdate,
    db: AsyncSession = Depends(get_db),
) -> AdminPostDetail:
    post = await update_admin_post(db, post_id, payload)
    return AdminPostDetail.model_validate(post)


@router.delete("/{post_id}", status_code=204)
async def delete_post(post_id: int, db: AsyncSession = Depends(get_db)) -> None:
    await delete_admin_post(db, post_id)
