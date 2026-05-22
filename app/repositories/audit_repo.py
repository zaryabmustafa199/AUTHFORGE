"""
Audit Log Repository — Database operations for audit trail records.

Writes immutable audit entries for every security-sensitive action.
These records are append-only — they should never be updated or deleted.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import func, desc
from app.models.audit_log import AuditLog
from app.utils.logging import get_logger
from typing import Optional, List
from uuid import UUID

logger = get_logger(__name__)


class AuditRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        action: str,
        user_id: Optional[UUID] = None,
        ip_address: Optional[str] = None,
        metadata_info: Optional[dict] = None,
    ) -> Optional[AuditLog]:
        """
        Creates an audit log entry. This should NEVER raise to the caller —
        a failure to write an audit log must not break the user's request.
        """
        try:
            entry = AuditLog(
                action=action,
                user_id=user_id,
                ip_address=ip_address,
                metadata_info=metadata_info or {},
            )
            self.session.add(entry)
            await self.session.commit()
            await self.session.refresh(entry)
            return entry
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error(
                "Failed to write audit log",
                extra={"action": action, "user_id": str(user_id), "error": str(exc)},
            )
            return None

    async def get_logs(
        self,
        page: int = 1,
        per_page: int = 50,
        user_id: Optional[UUID] = None,
        action: Optional[str] = None,
    ) -> tuple[List[AuditLog], int]:
        """
        Returns paginated audit logs with optional filters.
        Returns (logs, total_count).
        """
        try:
            query = select(AuditLog)

            if user_id:
                query = query.where(AuditLog.user_id == user_id)
            if action:
                query = query.where(AuditLog.action == action)

            # Get total count
            count_query = select(func.count()).select_from(query.subquery())
            total_result = await self.session.execute(count_query)
            total = total_result.scalar() or 0

            # Get paginated results (newest first)
            query = query.order_by(desc(AuditLog.created_at))
            query = query.offset((page - 1) * per_page).limit(per_page)

            result = await self.session.execute(query)
            logs = list(result.scalars().all())

            return logs, total
        except SQLAlchemyError as exc:
            logger.error("DB error fetching audit logs", extra={"error": str(exc)})
            raise
