from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile
from PIL import Image
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.concurrency import run_in_threadpool

from app.core.config import get_settings
from app.models.media import Media
from app.schemas.media import UploadResponse

MAX_UPLOAD_BYTES = 5 * 1024 * 1024
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}
ALLOWED_MIME = {
    "image/jpeg",
    "image/jpg",
    "image/png",
    "image/webp",
    "image/gif",
}
FORMAT_MAP = {
    "JPEG": (".jpg", "image/jpeg"),
    "PNG": (".png", "image/png"),
    "WEBP": (".webp", "image/webp"),
    "GIF": (".gif", "image/gif"),
}


def _inspect_image(data: bytes) -> tuple[str, str]:
    try:
        with Image.open(BytesIO(data)) as image:
            image.verify()
        with Image.open(BytesIO(data)) as image:
            image_format = (image.format or "").upper()
    except Exception:
        raise ValueError("不是有效图片")
    if image_format not in FORMAT_MAP:
        raise ValueError("不支持的图片格式")
    return FORMAT_MAP[image_format]


def _write_file(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)


async def save_upload(db: AsyncSession, file: UploadFile) -> UploadResponse:
    data = await file.read(MAX_UPLOAD_BYTES + 1)
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="文件超过 5 MB")
    if not data:
        raise HTTPException(status_code=422, detail="文件为空")

    original_ext = Path(file.filename or "").suffix.lower()
    if original_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=422, detail="不支持的扩展名")
    if file.content_type and file.content_type.lower() not in ALLOWED_MIME:
        raise HTTPException(status_code=422, detail="不支持的 MIME 类型")

    try:
        extension, mime = await run_in_threadpool(_inspect_image, data)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))

    now = datetime.now(timezone.utc)
    relative_dir = now.strftime("%Y/%m")
    filename = f"{relative_dir}/{uuid4().hex}{extension}"
    target = Path(get_settings().upload_dir) / filename
    await run_in_threadpool(_write_file, target, data)

    media = Media(
        filename=filename,
        original_name=file.filename or f"upload{extension}",
        mime=mime,
        size_bytes=len(data),
    )
    db.add(media)
    await db.commit()
    await db.refresh(media)

    return UploadResponse(
        url=f"/uploads/{filename}",
        filename=filename,
        mime=mime,
        size=len(data),
    )


async def list_media(
    db: AsyncSession, *, page: int, page_size: int
) -> tuple[list[Media], int]:
    total = await db.scalar(select(func.count()).select_from(Media)) or 0
    result = await db.execute(
        select(Media)
        .order_by(Media.created_at.desc(), Media.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    return list(result.scalars().all()), total


async def delete_media(db: AsyncSession, media_id: int) -> None:
    media = await db.get(Media, media_id)
    if media is None:
        raise HTTPException(status_code=404, detail="图片不存在")

    base = Path(get_settings().upload_dir).resolve()
    target = (base / media.filename).resolve()
    if not target.is_relative_to(base):
        raise HTTPException(status_code=400, detail="非法文件路径")
    if target.exists():
        await run_in_threadpool(target.unlink)

    await db.delete(media)
    await db.commit()
