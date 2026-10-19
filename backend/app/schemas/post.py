from datetime import datetime

from pydantic import BaseModel, ConfigDict


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    slug: str


class TagWithCount(BaseModel):
    name: str
    slug: str
    post_count: int


class PostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    excerpt: str
    cover_url: str | None
    language: str
    published_at: datetime | None
    view_count: int
    tags: list[TagOut]


class PostListResponse(BaseModel):
    items: list[PostListItem]
    total: int
    page: int
    page_size: int


class PostDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    slug: str
    title: str
    excerpt: str
    content_md: str
    cover_url: str | None
    language: str
    published_at: datetime | None
    updated_at: datetime
    view_count: int
    tags: list[TagOut]
