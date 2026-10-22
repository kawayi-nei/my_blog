from pydantic import BaseModel

from app.schemas.post import PostListItem
from app.schemas.project import ProjectListItem


class SearchResponse(BaseModel):
    posts: list[PostListItem]
    projects: list[ProjectListItem]
    total: int
