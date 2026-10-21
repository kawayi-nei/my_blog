from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.project import ProjectDetail, ProjectListItem
from app.services.projects import (
    get_public_project,
    list_public_projects,
    localize_project,
)

router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectListItem])
async def list_projects(
    featured: bool | None = None,
    locale: str = Query("zh", pattern="^(zh|en)$"),
    db: AsyncSession = Depends(get_db),
) -> list[ProjectListItem]:
    projects = await list_public_projects(
        db, locale=locale, featured=featured
    )
    return [
        ProjectListItem(**localize_project(project, locale))
        for project in projects
    ]


@router.get("/{slug}", response_model=ProjectDetail)
async def get_project(
    slug: str,
    locale: str = Query("zh", pattern="^(zh|en)$"),
    db: AsyncSession = Depends(get_db),
) -> ProjectDetail:
    project = await get_public_project(db, slug)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return ProjectDetail(
        **localize_project(project, locale, detail=True)
    )
