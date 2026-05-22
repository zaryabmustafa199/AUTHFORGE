"""
Auth Tests — Signup, Login, Token Refresh, Logout,
Email Verification, and Password Reset flows.
"""
import pytest
from httpx import AsyncClient


# ======================================================================
# Signup Tests
# ======================================================================

@pytest.mark.asyncio
async def test_signup_success(client: AsyncClient):
    """New user signup returns 201 with user data."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "newuser@test.com",
        "password": "ValidPass123!",
    })
    assert response.status_code == 201
    data = response.json()
    assert data["user"]["email"] == "newuser@test.com"
    assert data["user"]["is_verified"] is False
    assert data["user"]["is_active"] is True
    assert data["user"]["role_id"] == 1  # Default role = user


@pytest.mark.asyncio
async def test_signup_duplicate_email(client: AsyncClient):
    """Duplicate email returns 400."""
    await client.post("/api/v1/auth/signup", json={
        "email": "dupe@test.com",
        "password": "ValidPass123!",
    })
    response = await client.post("/api/v1/auth/signup", json={
        "email": "dupe@test.com",
        "password": "ValidPass123!",
    })
    assert response.status_code == 400
    assert "already registered" in response.json()["detail"]


@pytest.mark.asyncio
async def test_signup_weak_password(client: AsyncClient):
    """Password under 8 chars returns 422 (validation error)."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "weak@test.com",
        "password": "short",
    })
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_signup_invalid_email(client: AsyncClient):
    """Invalid email format returns 422."""
    response = await client.post("/api/v1/auth/signup", json={
        "email": "not-an-email",
        "password": "ValidPass123!",
    })
    assert response.status_code == 422


# ======================================================================
# Login Tests
# ======================================================================

@pytest.mark.asyncio
async def test_login_success(client: AsyncClient):
    """Valid credentials return access + refresh tokens."""
    await client.post("/api/v1/auth/signup", json={
        "email": "loginuser@test.com",
        "password": "ValidPass123!",
    })
    response = await client.post("/api/v1/auth/login", data={
        "username": "loginuser@test.com",
        "password": "ValidPass123!",
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient):
    """Wrong password returns 401."""
    await client.post("/api/v1/auth/signup", json={
        "email": "wrongpw@test.com",
        "password": "ValidPass123!",
    })
    response = await client.post("/api/v1/auth/login", data={
        "username": "wrongpw@test.com",
        "password": "WrongPass999!",
    })
    assert response.status_code == 401
    assert "Incorrect email or password" in response.json()["detail"]


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Non-existent email returns 401 (same as wrong password for security)."""
    response = await client.post("/api/v1/auth/login", data={
        "username": "nobody@test.com",
        "password": "SomePass123!",
    })
    assert response.status_code == 401


# ======================================================================
# Token Refresh Tests
# ======================================================================

@pytest.mark.asyncio
async def test_refresh_token_rotation(client: AsyncClient):
    """Refresh returns new token pair and the old refresh token should differ."""
    await client.post("/api/v1/auth/signup", json={
        "email": "refresh@test.com",
        "password": "ValidPass123!",
    })
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "refresh@test.com",
        "password": "ValidPass123!",
    })
    old_tokens = login_resp.json()

    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": old_tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 200
    new_tokens = refresh_resp.json()
    assert new_tokens["access_token"] != old_tokens["access_token"]
    assert new_tokens["refresh_token"] != old_tokens["refresh_token"]


@pytest.mark.asyncio
async def test_refresh_with_invalid_token(client: AsyncClient):
    """Invalid refresh token returns 401."""
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "not.a.valid.jwt"},
    )
    assert response.status_code == 401


# ======================================================================
# Logout Tests
# ======================================================================

@pytest.mark.asyncio
async def test_logout(client: AsyncClient):
    """Logout returns 204 and the refresh token becomes unusable."""
    await client.post("/api/v1/auth/signup", json={
        "email": "logoutuser@test.com",
        "password": "ValidPass123!",
    })
    login_resp = await client.post("/api/v1/auth/login", data={
        "username": "logoutuser@test.com",
        "password": "ValidPass123!",
    })
    tokens = login_resp.json()
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}

    # Logout
    logout_resp = await client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers=headers,
    )
    assert logout_resp.status_code == 204

    # Try to use the old refresh token — should fail
    refresh_resp = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": tokens["refresh_token"]},
    )
    assert refresh_resp.status_code == 401


# ======================================================================
# Health Check
# ======================================================================

@pytest.mark.asyncio
async def test_health_check(client: AsyncClient):
    """Health endpoint returns 200."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
