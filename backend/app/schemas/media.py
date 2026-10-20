from datetime import datetime

from pydantic import BaseModel


class UploadResponse(BaseModel):
    url: str
    filename: str
    mime: str
    size: int


class MediaOut(BaseModel):
    id: int
    url: str
    filename: str
    original_name: str
    mime: str
    size_bytes: int
    created_at: datetime


class MediaListResponse(BaseModel):
    items: list[MediaOut]
    total: int
    page: int
    page_size: int
