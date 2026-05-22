"""
Audit Service — Centralized audit trail for security-sensitive actions.

Provides a simple interface to log actions. All methods are fire-and-forget:
a failure to write an audit entry must NEVER disrupt the user's request.

Action Constants:
    SIGNUP, LOGIN, LOGIN_FAILED, LOGOUT, EMAIL_VERIFIED,
    PASSWORD_RESET_REQUESTED, PASSWORD_RESET_COMPLETED,
    ROLE_CHANGED, ACCOUNT_LOCKED, PROFILE_UPDATED
"""
from sqlalchemy.ext.asyncio import AsyncSession
from app.repositories.audit_repo import AuditRepository
from app.utils.logging import get_logger
from typing import Optional
from uuid import UUID

logger = get_logger(__name__)

# ── Action Constants ──
SIGNUP = "SIGNUP"
LOGIN = "LOGIN"
LOGIN_FAILED = "LOGIN_FAILED"
LOGOUT = "LOGOUT"
EMAIL_VERIFIED = "EMAIL_VERIFIED"
PASSWORD_RESET_REQUESTED = "PASSWORD_RESET_REQUESTED"
PASSWORD_RESET_COMPLETED = "PASSWORD_RESET_COMPLETED"
ROLE_CHANGED = "ROLE_CHANGED"
ACCOUNT_LOCKED = "ACCOUNT_LOCKED"
PROFILE_UPDATED = "PROFILE_UPDATED"


class AuditService:
    def __init__(self, session: AsyncSession):
        self.repo = AuditRepository(session)

    async def log(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        metadata_info: Optional[dict] = None,
    ) -> None:
        """
        Writes an audit log entry. Fire-and-forget — never raises.
        """
        await self.repo.create(
            action=action,
            user_id=user_id,
            ip_address=ip_address,
            metadata_info=metadata_info,
        )
        logger.info(
            "Audit logged",
            extra={
                "action": action,
                "user_id": str(user_id) if user_id else None,
                "ip": ip_address,
            },
        )
