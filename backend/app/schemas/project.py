from datetime import date

from pydantic import BaseModel


class ProjectListItem(BaseModel):
    slug: str
    title: str
    summary: str
    cover_url: str | None
    tech_stack: list[str]
    featured: bool
    started_on: date | None
    ended_on: date | None


class ProjectDetail(ProjectListItem):
    content_md: str
    repo_url: str | None
    demo_url: str | None
