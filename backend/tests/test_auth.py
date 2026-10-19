import pytest

from app.core.config import get_settings
from app.services.rate_limit import login_limiter


@pytest.fixture(autouse=True)
def reset_login_limiter():
    login_limiter.reset_all()
    yield


async def test_login_success(client, admin_user):
    settings = get_settings()
    response = await client.post(
        "/api/auth/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert response.status_code == 200
    assert response.json() == {"username": settings.admin_username}
    assert "access_token" in response.cookies


async def test_me_requires_login(client):
    response = await client.get("/api/auth/me")
    assert response.status_code == 401


async def test_wrong_password(client, admin_user):
    settings = get_settings()
    response = await client.post(
        "/api/auth/login",
        json={"username": settings.admin_username, "password": "wrong-password"},
    )
    assert response.status_code == 401


async def test_admin_disabled_returns_404(client, monkeypatch):
    monkeypatch.setenv("ADMIN_ENABLED", "false")
    get_settings.cache_clear()
    try:
        response = await client.post(
            "/api/auth/login",
            json={"username": "admin", "password": "test-password"},
        )
        assert response.status_code == 404

        config = await client.get("/api/site/config")
        assert config.status_code == 200
        assert config.json() == {"admin_enabled": False}
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
