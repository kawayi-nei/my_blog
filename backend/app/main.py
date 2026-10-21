from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.api import admin
from app.api.public import auth, posts, projects, site, tags
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api")
app.include_router(site.router, prefix="/api")
app.include_router(posts.router, prefix="/api")
app.include_router(tags.router, prefix="/api")
app.include_router(projects.router, prefix="/api")
app.include_router(admin.router, prefix="/api/admin")

upload_dir = Path(settings.upload_dir)
upload_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(upload_dir)), name="uploads")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
