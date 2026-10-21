from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.admin_project import (
    AdminProjectCreate,
    AdminProjectDetail,
    AdminProjectListItem,
    AdminProjectListResponse,
    AdminProjectUpdate,
)
from app.services.admin_projects import (
    create_admin_project,
    delete_admin_project,
    get_admin_project,
    list_admin_projects,
    update_admin_project,
)

router = APIRouter(prefix="/projects", tags=["admin-projects"])


@router.get("", response_model=AdminProjectListResponse)
async def list_projects(
    status: str | None = Query(None, pattern="^(draft|published)$"),
    q: str | None = Query(None, max_length=100),
    page: int = Query(1, ge=1, le=100_000),
    page_size: int = Query(10, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> AdminProjectListResponse:
    query = q.strip() if q else None
    projects, total = await list_admin_projects(
        db,
        page=page,
        page_size=page_size,
        status=status,
        q=query or None,
    )
    return AdminProjectListResponse(
        items=[
            AdminProjectListItem.model_validate(project)
            for project in projects
        ],
        total=total,
        page=page,
        page_size=page_size,
    )


@router.post("", response_model=AdminProjectDetail, status_code=201)
async def create_project(
    payload: AdminProjectCreate, db: AsyncSession = Depends(get_db)
) -> AdminProjectDetail:
    project = await create_admin_project(db, payload)
    return AdminProjectDetail.model_validate(project)


@router.get("/{project_id}", response_model=AdminProjectDetail)
async def get_project(
    project_id: int, db: AsyncSession = Depends(get_db)
) -> AdminProjectDetail:
    project = await get_admin_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    return AdminProjectDetail.model_validate(project)


@router.patch("/{project_id}", response_model=AdminProjectDetail)
async def update_project(
    project_id: int,
    payload: AdminProjectUpdate,
    db: AsyncSession = Depends(get_db),
) -> AdminProjectDetail:
    project = await update_admin_project(db, project_id, payload)
    return AdminProjectDetail.model_validate(project)


@router.delete("/{project_id}", status_code=204)
async def delete_project(
    project_id: int, db: AsyncSession = Depends(get_db)
) -> None:
    await delete_admin_project(db, project_id)
