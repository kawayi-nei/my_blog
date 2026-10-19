from pathlib import Path

import pytest_asyncio
from dotenv import load_dotenv

env_test = Path(__file__).resolve().parents[1] / ".env.test"
if not env_test.exists():
    raise RuntimeError(
        f"Missing {env_test}; copy .env.test.example and fill in credentials"
    )

load_dotenv(env_test, override=True)

from httpx import ASGITransport, AsyncClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c
