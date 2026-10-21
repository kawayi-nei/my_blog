from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project


def _other_locale(locale: str) -> str:
    return "en" if locale == "zh" else "zh"


def localize_project(
    project: Project, locale: str, *, detail: bool = False
) -> dict:
    other = _other_locale(locale)

    def pick(field: str) -> str:
        primary = getattr(project, f"{field}_{locale}") or ""
        fallback = getattr(project, f"{field}_{other}") or ""
        return primary or fallback

    data = {
        "slug": project.slug,
        "title": getattr(project, f"title_{locale}"),
        "summary": pick("summary"),
        "cover_url": project.cover_url,
        "tech_stack": project.tech_stack,
        "featured": project.featured,
        "started_on": project.started_on,
        "ended_on": project.ended_on,
    }
    if detail:
        data.update(
            {
                "content_md": pick("content_md"),
                "repo_url": project.repo_url,
                "demo_url": project.demo_url,
            }
        )
    return data


async def list_public_projects(
    db: AsyncSession, *, locale: str, featured: bool | None = None
) -> list[Project]:
    filters = [Project.status == "published"]
    if featured is True:
        filters.append(Project.featured.is_(True))

    result = await db.execute(
        select(Project)
        .where(*filters)
        .order_by(
            Project.featured.desc(),
            Project.sort_order.asc(),
            Project.started_on.desc().nullslast(),
            Project.id.desc(),
        )
    )
    return list(result.scalars().all())


async def get_public_project(
    db: AsyncSession, slug: str
) -> Project | None:
    result = await db.execute(
        select(Project).where(
            Project.slug == slug, Project.status == "published"
        )
    )
    return result.scalar_one_or_none()
