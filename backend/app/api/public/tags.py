from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.models.post import Post, post_tags
from app.models.tag import Tag
from app.schemas.post import TagWithCount

router = APIRouter(prefix="/tags", tags=["tags"])


@router.get("", response_model=list[TagWithCount])
async def list_tags(db: AsyncSession = Depends(get_db)) -> list[TagWithCount]:
    result = await db.execute(
        select(Tag.name, Tag.slug, func.count(Post.id))
        .outerjoin(post_tags, Tag.id == post_tags.c.tag_id)
        .outerjoin(
            Post,
            (Post.id == post_tags.c.post_id) & (Post.status == "published"),
        )
        .group_by(Tag.id)
        .order_by(Tag.name)
    )
    return [
        TagWithCount(name=name, slug=slug, post_count=count)
        for name, slug, count in result.all()
    ]
