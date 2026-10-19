from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.post import PostDetail, PostListItem, PostListResponse
from app.services.posts import get_published_post, list_published_posts

router = APIRouter(prefix="/posts", tags=["posts"])


@router.get("", response_model=PostListResponse)
async def list_posts(
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(10, ge=1, le=50),
    tag: str | None = None,
    language: str | None = Query(None, pattern="^(zh|en)$"),
    db: AsyncSession = Depends(get_db),
) -> PostListResponse:
    posts, total = await list_published_posts(
        db, page=page, page_size=page_size, tag=tag, language=language
    )
    return PostListResponse(
        items=[PostListItem.model_validate(post) for post in posts],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.get("/{slug}", response_model=PostDetail)
async def get_post(slug: str, db: AsyncSession = Depends(get_db)) -> PostDetail:
    post = await get_published_post(db, slug)
    if post is None:
        raise HTTPException(status_code=404, detail="文章不存在")
    return PostDetail.model_validate(post)
