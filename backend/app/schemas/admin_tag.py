from pydantic import BaseModel, ConfigDict, Field


class AdminTagCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    slug: str = Field(min_length=1, max_length=50, pattern=r"^[a-z0-9-]+$")


class AdminTagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    slug: str
