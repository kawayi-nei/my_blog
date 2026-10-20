from fastapi import FastAPI

from app.api import admin
from app.api.public import auth, posts, site, tags
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api")
app.include_router(site.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
