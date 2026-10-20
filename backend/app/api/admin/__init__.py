from fastapi import APIRouter, Depends

from app.api.admin import media, posts, tags, uploads
from app.api.deps import require_admin, require_same_origin

router = APIRouter(
    dependencies=[Depends(require_admin), Depends(require_same_origin)]
)
router.include_router(tags.router)
router.include_router(posts.router)
router.include_router(uploads.router)
router.include_router(media.router)
