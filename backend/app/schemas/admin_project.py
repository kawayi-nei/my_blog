from datetime import date, datetime
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
    model_validator,
)

ProjectStatus = Literal["draft", "published"]
SLUG_PATTERN = r"^[a-z0-9-]+$"


def _normalize_tech_stack(value: list[str]) -> list[str]:
    normalized: list[str] = []
    for item in value:
        item = item.strip()
        if item and item not in normalized:
            normalized.append(item)
    if len(normalized) > 20:
        raise ValueError("技术栈最多 20 项")
    if any(len(item) > 50 for item in normalized):
        raise ValueError("技术栈每项最多 50 字符")
    return normalized


class AdminProjectCreate(BaseModel):
    slug: str = Field(min_length=1, max_length=200, pattern=SLUG_PATTERN)
    title_zh: str = Field(min_length=1, max_length=200)
    title_en: str = Field(min_length=1, max_length=200)
    summary_zh: str = Field(default="", max_length=500)
    summary_en: str = Field(default="", max_length=500)
    content_md_zh: str = ""
    content_md_en: str = ""
    cover_url: str | None = Field(default=None, max_length=500)
    tech_stack: list[str] = Field(default_factory=list)
    repo_url: str | None = Field(default=None, max_length=500)
    demo_url: str | None = Field(default=None, max_length=500)
    started_on: date | None = None
    ended_on: date | None = None
    featured: bool = False
    sort_order: int = 0
    status: ProjectStatus = "draft"

    @field_validator("tech_stack")
    @classmethod
    def validate_tech_stack(cls, value: list[str]) -> list[str]:
        return _normalize_tech_stack(value)

    @model_validator(mode="after")
    def validate_dates(self) -> "AdminProjectCreate":
        if (
            self.started_on
            and self.ended_on
            and self.ended_on < self.started_on
        ):
            raise ValueError("结束日期不能早于开始日期")
        return self


class AdminProjectUpdate(BaseModel):
    slug: str | None = Field(
        default=None, min_length=1, max_length=200, pattern=SLUG_PATTERN
    )
    title_zh: str | None = Field(default=None, min_length=1, max_length=200)
    title_en: str | None = Field(default=None, min_length=1, max_length=200)
    summary_zh: str | None = Field(default=None, max_length=500)
    summary_en: str | None = Field(default=None, max_length=500)
    content_md_zh: str | None = None
    content_md_en: str | None = None
    cover_url: str | None = Field(default=None, max_length=500)
    tech_stack: list[str] | None = None
    repo_url: str | None = Field(default=None, max_length=500)
    demo_url: str | None = Field(default=None, max_length=500)
    started_on: date | None = None
    ended_on: date | None = None
    featured: bool | None = None
    sort_order: int | None = None
    status: ProjectStatus | None = None

    @field_validator("tech_stack")
    @classmethod
    def validate_tech_stack(
        cls, value: list[str] | None
    ) -> list[str] | None:
        if value is None:
            return None
        return _normalize_tech_stack(value)


class AdminProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    slug: str
    title_zh: str
    title_en: str
    status: str
    featured: bool
    sort_order: int
    started_on: date | None
    ended_on: date | None
    cover_url: str | None
    updated_at: datetime


class AdminProjectListResponse(BaseModel):
    items: list[AdminProjectListItem]
    total: int
    page: int
    page_size: int


class AdminProjectDetail(AdminProjectListItem):
    summary_zh: str
    summary_en: str
    content_md_zh: str
    content_md_en: str
    tech_stack: list[str]
    repo_url: str | None
    demo_url: str | None
    created_at: datetime
