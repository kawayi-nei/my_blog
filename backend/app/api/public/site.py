from fastapi import APIRouter

from app.core.config import get_settings
from app.schemas.site import SiteConfigResponse

router = APIRouter(prefix="/site", tags=["site"])


@router.get("/config", response_model=SiteConfigResponse)
async def site_config() -> SiteConfigResponse:
    return SiteConfigResponse(admin_enabled=get_settings().admin_enabled)
