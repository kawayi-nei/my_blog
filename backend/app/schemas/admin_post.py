from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.admin_tag import AdminTagOut

PostStatus = Literal["draft", "published"]
PostLanguage = Literal["zh", "en"]
SLUG_PATTERN = r"^[a-z0-9-]+$"


class AdminPostCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=200, pattern=SLUG_PATTERN)
    title: str = Field(min_length=1, max_length=200)
    excerpt: str = Field(default="", max_length=500)
    content_md: str
    language: PostLanguage = "zh"
    status: PostStatus = "draft"
    tag_ids: list[int] = Field(default_factory=list)


class AdminPostUpdate(BaseModel):
    slug: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=SLUG_PATTERN
    )
    title: str | None = Field(default=None, min_length=1, max_length=200)
    excerpt: str | None = Field(default=None, max_length=500)
    content_md: str | None = None
    language: PostLanguage | None = None
    status: PostStatus | None = None
    tag_ids: list[int] | None = None


class AdminPostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title: str
    excerpt: str
    language: str
    status: str
    published_at: datetime | None
    updated_at: datetime
    tags: list[AdminTagOut]


class AdminPostListResponse(BaseModel):
    items: list[AdminPostListItem]
    total: int
    page: int
    page_size: int


class AdminPostDetail(AdminPostListItem):
    content_md: str
    created_at: datetime
