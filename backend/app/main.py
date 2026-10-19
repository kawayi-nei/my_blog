from fastapi import FastAPI

from app.api.public import auth, site
from app.core.config import get_settings

settings = get_settings()
app = FastAPI(title=settings.app_name)

app.include_router(auth.router, prefix="/api")
app.include_router(site.router, prefix="/api")


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
