"""
Session Repository — Database operations for Session records.

All methods include proper exception handling with transaction rollback
to prevent inconsistent database state on failures.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError
from app.models.session import Session
from app.utils.logging import get_logger
from typing import List, Optional
from uuid import UUID

logger = get_logger(__name__)


class SessionRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create(
        self,
        user_id: UUID,
        refresh_token_hash: str,
        expires_at,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> Session:
        try:
            db_session = Session(
                user_id=user_id,
                refresh_token_hash=refresh_token_hash,
                expires_at=expires_at,
                device_info=device_info,
                ip_address=ip_address,
            )
            self.session.add(db_session)
            await self.session.commit()
            await self.session.refresh(db_session)
            logger.info("Session created", extra={"session_id": str(db_session.id), "user_id": str(user_id)})
            return db_session
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("DB error creating session", extra={"user_id": str(user_id), "error": str(exc)})
            raise

    async def get_active_sessions_for_user(self, user_id: UUID) -> List[Session]:
        try:
            result = await self.session.execute(
                select(Session).where(
                    Session.user_id == user_id,
                    Session.is_revoked == False,  # noqa: E712
                )
            )
            return list(result.scalars().all())
        except SQLAlchemyError as exc:
            logger.error("DB error fetching sessions", extra={"user_id": str(user_id), "error": str(exc)})
            raise

    async def get_by_id(self, session_id: UUID) -> Optional[Session]:
        try:
            result = await self.session.execute(select(Session).where(Session.id == session_id))
            return result.scalars().first()
        except SQLAlchemyError as exc:
            logger.error("DB error fetching session by id", extra={"session_id": str(session_id), "error": str(exc)})
            raise

    async def revoke(self, session: Session) -> None:
        try:
            session.is_revoked = True
            await self.session.commit()
            logger.info("Session revoked", extra={"session_id": str(session.id), "user_id": str(session.user_id)})
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("DB error revoking session", extra={"session_id": str(session.id), "error": str(exc)})
            raise
