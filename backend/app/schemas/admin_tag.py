from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdminTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")


class AdminTagUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=50)
    slug: str | None = Field(
        default=None, min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$"
    )

    @model_validator(mode="after")
    def require_at_least_one(self) -> "AdminTagUpdate":
        if self.name is None and self.slug is None:
            raise ValueError("name or slug is required")
        return self


class AdminTagRef(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str


class AdminTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
    post_count: int
