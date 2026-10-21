from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.project import Project
from app.schemas.admin_project import (
    AdminProjectCreate,
    AdminProjectUpdate,
)


async def list_admin_projects(
    db: AsyncSession,
    *,
    page: int,
    page_size: int,
    status: str | None = None,
    q: str | None = None,
) -> tuple[list[Project], int]:
    filters = []
    if status:
        filters.append(Project.status == status)
    if q:
        pattern = f"%{q}%"
        filters.append(
            or_(
                Project.slug.ilike(pattern),
                Project.title_zh.ilike(pattern),
                Project.title_en.ilike(pattern),
            )
        )

    total = (
        await db.scalar(
            select(func.count()).select_from(Project).where(*filters)
        )
        or 0
    )
    result = await db.execute(
        select(Project)
        .where(*filters)
        .options(
            defer(Project.content_md_zh),
            defer(Project.content_md_en),
        )
        .order_by(Project.updated_at.desc(), Project.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def get_admin_project(
    db: AsyncSession, project_id: int
) -> Project | None:
    result = await db.execute(
        select(Project).where(Project.id == project_id)
    )
    return result.scalar_one_or_none()


async def _ensure_slug_available(
    db: AsyncSession, slug: str, *, exclude_id: int | None = None
) -> None:
    query = select(Project.id).where(Project.slug == slug)
    if exclude_id is not None:
        query = query.where(Project.id != exclude_id)
    if await db.scalar(query) is not None:
        raise HTTPException(status_code=409, detail="slug 已存在")


def _validate_date_order(started_on, ended_on) -> None:
    if started_on and ended_on and ended_on < started_on:
        raise HTTPException(
            status_code=422, detail="结束日期不能早于开始日期"
        )


async def create_admin_project(
    db: AsyncSession, data: AdminProjectCreate
) -> Project:
    await _ensure_slug_available(db, data.slug)
    project = Project(
        slug=data.slug,
        title_zh=data.title_zh,
        title_en=data.title_en,
        summary_zh=data.summary_zh,
        summary_en=data.summary_en,
        content_md_zh=data.content_md_zh,
        content_md_en=data.content_md_en,
        cover_url=data.cover_url,
        tech_stack=data.tech_stack,
        repo_url=data.repo_url,
        demo_url=data.demo_url,
        started_on=data.started_on,
        ended_on=data.ended_on,
        featured=data.featured,
        sort_order=data.sort_order,
        status=data.status,
    )
    db.add(project)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug 已存在")
    await db.refresh(project)
    return project


async def update_admin_project(
    db: AsyncSession, project_id: int, data: AdminProjectUpdate
) -> Project:
    project = await get_admin_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")

    changes = data.model_dump(exclude_unset=True)
    nullable = {
        "cover_url",
        "repo_url",
        "demo_url",
        "started_on",
        "ended_on",
    }
    changes = {
        key: value
        for key, value in changes.items()
        if value is not None or key in nullable
    }

    new_slug = changes.get("slug")
    if new_slug is not None and new_slug != project.slug:
        await _ensure_slug_available(
            db, new_slug, exclude_id=project.id
        )

    started_on = changes.get("started_on", project.started_on)
    ended_on = changes.get("ended_on", project.ended_on)
    _validate_date_order(started_on, ended_on)

    for field, value in changes.items():
        setattr(project, field, value)

    project.updated_at = datetime.now(timezone.utc)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(status_code=409, detail="slug 已存在")
    await db.refresh(project)
    return project


async def delete_admin_project(
    db: AsyncSession, project_id: int
) -> None:
    project = await get_admin_project(db, project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="项目不存在")
    await db.delete(project)
    await db.commit()
