from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.post import PostListItem
from app.schemas.project import ProjectListItem
from app.schemas.search import SearchResponse
from app.services.projects import localize_project
from app.services.search import search_all

router = APIRouter(prefix="/search", tags=["search"])


@router.get("", response_model=SearchResponse)
async def search(
    q: str = Query(..., max_length=100),
    locale: str = Query("zh", pattern="^(zh|en)$"),
    db: AsyncSession = Depends(get_db),
) -> SearchResponse:
    posts, projects, total = await search_all(db, q=q, locale=locale)
    return SearchResponse(
        posts=[PostListItem.model_validate(post) for post in posts],
        projects=[
            ProjectListItem(**localize_project(project, locale))
            for project in projects
        ],
        total=total,
    )
