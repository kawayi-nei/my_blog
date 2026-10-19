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


async def test_me_after_login(client, admin_user):
    settings = get_settings()
    response = await client.post(
        "/api/auth/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert response.status_code == 200

    me = await client.get("/api/auth/me")
    assert me.status_code == 200
    assert me.json() == {"username": settings.admin_username}


async def test_login_cookie_attributes(client, admin_user):
    settings = get_settings()
    response = await client.post(
        "/api/auth/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert response.status_code == 200

    set_cookie = response.headers["set-cookie"]
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Path=/" in set_cookie
    assert f"Max-Age={settings.jwt_expire_days * 86400}" in set_cookie


async def test_logout_clears_cookie(client, admin_user):
    settings = get_settings()
    login = await client.post(
        "/api/auth/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert login.status_code == 200

    response = await client.post("/api/auth/logout")
    assert response.status_code == 204
    set_cookie = response.headers["set-cookie"]
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "SameSite=lax" in set_cookie

    me = await client.get("/api/auth/me")
    assert me.status_code == 401


async def test_logout_secure_cookie_attributes(client, admin_user, monkeypatch):
    settings = get_settings()
    monkeypatch.setenv("COOKIE_SECURE", "true")
    get_settings.cache_clear()
    try:
        login = await client.post(
            "/api/auth/login",
            json={
                "username": settings.admin_username,
                "password": settings.admin_password,
            },
        )
        assert login.status_code == 200
        assert "Secure" in login.headers["set-cookie"]

        response = await client.post("/api/auth/logout")
        assert response.status_code == 204
        assert "Secure" in response.headers["set-cookie"]
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()


async def test_invalid_token(client):
    response = await client.get(
        "/api/auth/me", cookies={"access_token": "not-a-jwt"}
    )
    assert response.status_code == 401


async def test_login_rate_limit(client, admin_user):
    settings = get_settings()
    for _ in range(5):
        response = await client.post(
            "/api/auth/login",
            json={"username": settings.admin_username, "password": "wrong-password"},
        )
        assert response.status_code == 401

    response = await client.post(
        "/api/auth/login",
        json={
            "username": settings.admin_username,
            "password": settings.admin_password,
        },
    )
    assert response.status_code == 429


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

        logout = await client.post("/api/auth/logout")
        assert logout.status_code == 404

        me = await client.get("/api/auth/me")
        assert me.status_code == 401
    finally:
        monkeypatch.undo()
        get_settings.cache_clear()
