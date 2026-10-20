from fastapi import APIRouter, Depends, File, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.media import UploadResponse
from app.services.media import save_upload

router = APIRouter(prefix="/uploads", tags=["admin-uploads"])


@router.post("", response_model=UploadResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
) -> UploadResponse:
    return await save_upload(db, file)
