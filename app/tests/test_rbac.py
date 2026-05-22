"""
RBAC Tests — Role-based access control and admin endpoints.
"""
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_get_profile(client: AsyncClient, auth_headers):
    """Authenticated user can view their own profile."""
    headers, _ = auth_headers
    response = await client.get("/api/v1/users/me", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "testuser@test.com"
    assert data["role_id"] == 1


@pytest.mark.asyncio
async def test_get_profile_unauthenticated(client: AsyncClient):
    """Unauthenticated request to /me returns 401."""
    response = await client.get("/api/v1/users/me")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, auth_headers):
    """User can update their own full_name."""
    headers, _ = auth_headers
    response = await client.patch(
        "/api/v1/users/me",
        json={"full_name": "Test User"},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["full_name"] == "Test User"


@pytest.mark.asyncio
async def test_admin_list_users(client: AsyncClient, admin_headers):
    """Admin can list all users."""
    headers, _ = admin_headers
    response = await client.get("/api/v1/users/admin/users", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "users" in data
    assert "total" in data
    assert data["total"] >= 1


@pytest.mark.asyncio
async def test_regular_user_cannot_access_admin(client: AsyncClient, auth_headers):
    """Regular user (role=user) gets 403 on admin endpoints."""
    headers, _ = auth_headers
    response = await client.get("/api/v1/users/admin/users", headers=headers)
    assert response.status_code == 403
    assert "Insufficient permissions" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_change_user_role(client: AsyncClient, admin_headers, db_session: AsyncSession):
    """Admin can change another user's role."""
    headers, _ = admin_headers

    # Create a target user
    await client.post("/api/v1/auth/signup", json={
        "email": "targetrole@test.com",
        "password": "ValidPass123!",
    })

    # Find their ID
    from sqlalchemy.future import select
    from app.models.user import User
    result = await db_session.execute(select(User).where(User.email == "targetrole@test.com"))
    target_user = result.scalars().first()

    # Change role to moderator (id=2)
    response = await client.patch(
        f"/api/v1/users/admin/users/{target_user.id}",
        json={"role_id": 2},
        headers=headers,
    )
    assert response.status_code == 200
    assert response.json()["role_id"] == 2


@pytest.mark.asyncio
async def test_admin_cannot_change_own_role(client: AsyncClient, admin_headers):
    """Admin cannot change their own role (safety guard)."""
    headers, _ = admin_headers

    # Get own user ID from /me
    me_resp = await client.get("/api/v1/users/me", headers=headers)
    my_id = me_resp.json()["id"]

    response = await client.patch(
        f"/api/v1/users/admin/users/{my_id}",
        json={"role_id": 1},
        headers=headers,
    )
    assert response.status_code == 400
    assert "Cannot change your own role" in response.json()["detail"]


@pytest.mark.asyncio
async def test_admin_audit_logs(client: AsyncClient, admin_headers):
    """Admin can view audit logs."""
    headers, _ = admin_headers
    response = await client.get("/api/v1/users/admin/audit-logs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "logs" in data
    assert "total" in data
    assert data["total"] >= 1  # At least the signup/login actions from fixture
