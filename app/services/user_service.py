"""
User Service — Business logic for user profile management and admin operations.

Handles profile viewing, profile updates, user listing (admin),
and role changes (admin).
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func

from app.repositories.user_repo import UserRepository
from app.models.user import User
from app.models.role import Role
from app.schemas.user import UserProfileUpdate, AdminUserUpdate
from app.services.audit_service import AuditService, PROFILE_UPDATED, ROLE_CHANGED
from app.utils.logging import get_logger
from typing import Optional, List
from uuid import UUID

logger = get_logger(__name__)


class UserService:
    def __init__(self, session: AsyncSession):
        self.session = session
        self.user_repo = UserRepository(session)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------
    # Self-Service Profile
    # ------------------------------------------------------------------
    async def update_profile(
        self,
        user: User,
        update_data: UserProfileUpdate,
        ip_address: Optional[str] = None,
    ) -> User:
        """
        Updates the authenticated user's own profile.
        Only allows changing full_name (limited fields for self-service).
        """
        changes = {}

        if update_data.full_name is not None:
            changes["full_name"] = {"old": user.full_name, "new": update_data.full_name}
            user.full_name = update_data.full_name

        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update",
            )

        updated_user = await self.user_repo.update(user)

        await self.audit.log(
            action=PROFILE_UPDATED,
            user_id=user.id,
            ip_address=ip_address,
            metadata_info={"changes": changes},
        )

        logger.info("Profile updated", extra={"user_id": str(user.id), "changes": changes})
        return updated_user

    # ------------------------------------------------------------------
    # Admin: List Users
    # ------------------------------------------------------------------
    async def list_users(
        self,
        page: int = 1,
        per_page: int = 20,
    ) -> tuple[List[User], int]:
        """
        Returns a paginated list of all users with their roles.
        Admin-only.
        """
        try:
            query = (
                select(User)
                .options(selectinload(User.role))
                .order_by(User.created_at.desc())
                .offset((page - 1) * per_page)
                .limit(per_page)
            )
            result = await self.session.execute(query)
            users = list(result.scalars().all())

            count_result = await self.session.execute(select(func.count(User.id)))
            total = count_result.scalar() or 0

            return users, total
        except SQLAlchemyError as exc:
            logger.error("DB error listing users", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

    # ------------------------------------------------------------------
    # Admin: Get Single User
    # ------------------------------------------------------------------
    async def get_user_by_id(self, user_id: UUID) -> User:
        """Fetches a single user with role info. Admin-only."""
        try:
            result = await self.session.execute(
                select(User)
                .options(selectinload(User.role))
                .where(User.id == user_id)
            )
            user = result.scalars().first()
        except SQLAlchemyError as exc:
            logger.error("DB error fetching user", extra={"user_id": str(user_id), "error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )
        return user

    # ------------------------------------------------------------------
    # Admin: Update User (Role, Active Status)
    # ------------------------------------------------------------------
    async def admin_update_user(
        self,
        target_user_id: UUID,
        update_data: AdminUserUpdate,
        admin_user: User,
        ip_address: Optional[str] = None,
    ) -> User:
        """
        Admin-only: changes a user's role, active status, or verified status.
        Logs every change to the audit trail.
        """
        target_user = await self.get_user_by_id(target_user_id)
        changes = {}

        # Prevent admin from demoting themselves
        if target_user.id == admin_user.id and update_data.role_id is not None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot change your own role",
            )

        # Role change
        if update_data.role_id is not None:
            # Validate role exists
            try:
                role_result = await self.session.execute(
                    select(Role).where(Role.id == update_data.role_id)
                )
                new_role = role_result.scalars().first()
            except SQLAlchemyError as exc:
                logger.error("DB error validating role", extra={"error": str(exc)})
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail="Service temporarily unavailable",
                )

            if not new_role:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Role with id {update_data.role_id} does not exist",
                )

            old_role_name = target_user.role.name if target_user.role else "unknown"
            changes["role"] = {"old": old_role_name, "new": new_role.name}
            target_user.role_id = update_data.role_id

        # Active status change
        if update_data.is_active is not None:
            changes["is_active"] = {"old": target_user.is_active, "new": update_data.is_active}
            target_user.is_active = update_data.is_active

        # Verified status change
        if update_data.is_verified is not None:
            changes["is_verified"] = {"old": target_user.is_verified, "new": update_data.is_verified}
            target_user.is_verified = update_data.is_verified

        if not changes:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid fields to update",
            )

        updated_user = await self.user_repo.update(target_user)

        # Audit every change with full before/after context
        for field, diff in changes.items():
            action = ROLE_CHANGED if field == "role" else PROFILE_UPDATED
            await self.audit.log(
                action=action,
                user_id=target_user.id,
                ip_address=ip_address,
                metadata_info={
                    "field": field,
                    "old_value": str(diff["old"]),
                    "new_value": str(diff["new"]),
                    "changed_by": str(admin_user.id),
                },
            )

        logger.info(
            "Admin updated user",
            extra={
                "admin_id": str(admin_user.id),
                "target_user_id": str(target_user_id),
                "changes": changes,
            },
        )
        return updated_user
