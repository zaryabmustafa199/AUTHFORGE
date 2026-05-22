"""
User Routes — Profile management and admin endpoints.

- /users/me: Authenticated user's own profile (GET, PATCH)
- /admin/users: Admin-only user management (GET, PATCH role)
- /admin/audit-logs: Admin-only audit trail viewer
"""
from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_db, get_current_user, require_role
from app.schemas.user import (
    UserResponse, UserDetailResponse, UserProfileUpdate,
    AdminUserUpdate, PaginatedUsersResponse,
)
from app.schemas.audit import AuditLogResponse, PaginatedAuditLogsResponse
from app.services.user_service import UserService
from app.repositories.audit_repo import AuditRepository
from app.models.user import User
from typing import Optional
from uuid import UUID

router = APIRouter()


# ======================================================================
# Self-Service Profile Endpoints
# ======================================================================

@router.get("/me", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    """Get the authenticated user's profile."""
    return current_user


@router.patch("/me", response_model=UserResponse)
async def update_my_profile(
    request: Request,
    update_data: UserProfileUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Update the authenticated user's profile. Only full_name can be changed."""
    user_service = UserService(db)
    ip_address = request.client.host if request.client else None
    return await user_service.update_profile(current_user, update_data, ip_address)


# ======================================================================
# Admin Endpoints
# ======================================================================

@router.get(
    "/admin/users",
    response_model=PaginatedUsersResponse,
    dependencies=[Depends(require_role(["admin"]))],
)
async def list_all_users(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(20, ge=1, le=100, description="Items per page"),
    db: AsyncSession = Depends(get_db),
):
    """
    List all users with pagination. Admin-only.
    Returns users with their role information.
    """
    user_service = UserService(db)
    users, total = await user_service.list_users(page=page, per_page=per_page)
    return {
        "users": users,
        "total": total,
        "page": page,
        "per_page": per_page,
    }


@router.get(
    "/admin/users/{user_id}",
    response_model=UserDetailResponse,
    dependencies=[Depends(require_role(["admin"]))],
)
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get detailed info about a specific user. Admin-only."""
    user_service = UserService(db)
    return await user_service.get_user_by_id(user_id)


@router.patch(
    "/admin/users/{user_id}",
    response_model=UserDetailResponse,
)
async def admin_update_user(
    request: Request,
    user_id: UUID,
    update_data: AdminUserUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(require_role(["admin"])),
):
    """
    Update a user's role, active status, or verified status. Admin-only.
    Cannot change your own role (safety guard).
    """
    user_service = UserService(db)
    ip_address = request.client.host if request.client else None
    return await user_service.admin_update_user(user_id, update_data, current_user, ip_address)


# ======================================================================
# Admin: Audit Log Viewer
# ======================================================================

@router.get(
    "/admin/audit-logs",
    response_model=PaginatedAuditLogsResponse,
    dependencies=[Depends(require_role(["admin"]))],
)
async def list_audit_logs(
    page: int = Query(1, ge=1, description="Page number"),
    per_page: int = Query(50, ge=1, le=100, description="Items per page"),
    user_id: Optional[UUID] = Query(None, description="Filter by user ID"),
    action: Optional[str] = Query(None, description="Filter by action (e.g., LOGIN, SIGNUP)"),
    db: AsyncSession = Depends(get_db),
):
    """
    View the audit trail. Admin-only.
    Supports filtering by user_id and action type.
    """
    audit_repo = AuditRepository(db)
    logs, total = await audit_repo.get_logs(
        page=page, per_page=per_page, user_id=user_id, action=action,
    )
    return {
        "logs": logs,
        "total": total,
        "page": page,
        "per_page": per_page,
    }
