"""
Session Service — Business logic for session management.

Handles session creation (with hashed tokens), revocation,
and Redis-based token blacklisting.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from redis.asyncio import Redis
from redis.exceptions import RedisError
from app.repositories.session_repo import SessionRepository
from app.utils.security import get_password_hash
from app.utils.logging import get_logger
from typing import Optional
from uuid import UUID
from datetime import datetime

logger = get_logger(__name__)


class SessionService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.session_repo = SessionRepository(session)
        self.redis = redis

    async def create_session(
        self,
        user_id: UUID,
        refresh_token: str,
        expires_at: datetime,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """
        Creates a new session record with a hashed refresh token.
        The raw token is NEVER stored — only the bcrypt hash.
        """
        token_hash = get_password_hash(refresh_token)
        return await self.session_repo.create(
            user_id, token_hash, expires_at, device_info, ip_address,
        )

    async def revoke_session(self, session_id: UUID, current_user_id: UUID) -> None:
        """
        Revokes a specific session. Enforces ownership — users can
        only revoke their own sessions.
        """
        session = await self.session_repo.get_by_id(session_id)
        if not session or session.user_id != current_user_id:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found",
            )
        await self.session_repo.revoke(session)
        logger.info(
            "Session revoked by user",
            extra={"session_id": str(session_id), "user_id": str(current_user_id)},
        )

    async def blacklist_token(self, jti: str, expires_delta) -> None:
        """
        Adds a token's JTI to the Redis blacklist.
        TTL is set to the token's remaining lifetime so the key
        auto-deletes once the token would have expired anyway.
        """
        seconds_remaining = int(expires_delta.total_seconds())
        if seconds_remaining <= 0:
            return

        try:
            await self.redis.setex(f"blacklist:{jti}", seconds_remaining, "1")
            logger.info("Token blacklisted", extra={"jti": jti, "ttl_seconds": seconds_remaining})
        except RedisError as exc:
            logger.error("Redis error blacklisting token", extra={"jti": jti, "error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

    async def is_blacklisted(self, jti: str) -> bool:
        """Checks if a token's JTI is in the Redis blacklist."""
        try:
            exists = await self.redis.exists(f"blacklist:{jti}")
            return exists > 0
        except RedisError as exc:
            logger.error("Redis error checking blacklist", extra={"jti": jti, "error": str(exc)})
            # Fail closed: if Redis is down, reject the token for safety
            return True
