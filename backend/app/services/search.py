from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from app.models.post import Post
from app.models.project import Project

SEARCH_LIMIT = 10
_LIKE_ESCAPE = "\\"


def escape_like(value: str) -> str:
    return (
        value.replace(_LIKE_ESCAPE, _LIKE_ESCAPE * 2)
        .replace("%", _LIKE_ESCAPE + "%")
        .replace("_", _LIKE_ESCAPE + "_")
    )


async def search_posts(db: AsyncSession, q: str) -> list[Post]:
    pattern = f"%{escape_like(q)}%"
    fields = [Post.title, Post.excerpt, Post.content_md]
    match = or_(*[field.ilike(pattern, escape=_LIKE_ESCAPE) for field in fields])
    score = func.greatest(*[func.similarity(field, q) for field in fields])

    result = await db.execute(
        select(Post)
        .where(Post.status == "published", match)
        .options(defer(Post.content_md))
        .order_by(
            score.desc(),
            Post.published_at.desc().nulls_last(),
            Post.id.desc(),
        )
        .limit(SEARCH_LIMIT)
    )
    return list(result.scalars().unique())


async def search_projects(
    db: AsyncSession, q: str, locale: str
) -> list[Project]:
    pattern = f"%{escape_like(q)}%"
    fields = [
        getattr(Project, f"title_{locale}"),
        getattr(Project, f"summary_{locale}"),
        getattr(Project, f"content_md_{locale}"),
    ]
    match = or_(*[field.ilike(pattern, escape=_LIKE_ESCAPE) for field in fields])
    score = func.greatest(*[func.similarity(field, q) for field in fields])

    result = await db.execute(
        select(Project)
        .where(Project.status == "published", match)
        .order_by(
            score.desc(),
            Project.featured.desc(),
            Project.sort_order.asc(),
            Project.id.desc(),
        )
        .limit(SEARCH_LIMIT)
    )
    return list(result.scalars().all())


async def search_all(
    db: AsyncSession, *, q: str, locale: str
) -> tuple[list[Post], list[Project], int]:
    term = q.strip()
    if not term:
        return [], [], 0

    posts = await search_posts(db, term)
    projects = await search_projects(db, term, locale)
    return posts, projects, len(posts) + len(projects)
