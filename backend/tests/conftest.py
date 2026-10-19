from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / ".env.test", override=True)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
