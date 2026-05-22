"""
Auth Service — Core business logic for all authentication flows.

Orchestrates user repository, token service, session service, audit service,
and Redis for signup, login, token refresh, logout, email verification,
password reset, and brute-force protection.
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from redis.asyncio import Redis
from redis.exceptions import RedisError

from app.repositories.user_repo import UserRepository
from app.schemas.user import UserCreate
from app.services.token_service import TokenService
from app.services.session_service import SessionService
from app.services.audit_service import (
    AuditService, SIGNUP, LOGIN, LOGIN_FAILED, LOGOUT,
    EMAIL_VERIFIED, PASSWORD_RESET_REQUESTED, PASSWORD_RESET_COMPLETED,
    ACCOUNT_LOCKED,
)
from app.utils.security import verify_password, get_password_hash, generate_otp, generate_reset_token
from app.utils.logging import get_logger
from app.models.user import User
from datetime import datetime, timezone

logger = get_logger(__name__)

# Redis TTLs (seconds)
OTP_TTL = 600            # 10 minutes for email verification OTP
RESET_TOKEN_TTL = 900    # 15 minutes for password reset token
EMAIL_COOLDOWN_TTL = 60  # 60 seconds between email sends

# Brute-force protection
MAX_FAILED_LOGINS = 5    # Lock after 5 failed attempts
LOCKOUT_TTL = 900        # 15 minute lockout


class AuthService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.user_repo = UserRepository(session)
        self.token_service = TokenService()
        self.session_service = SessionService(session, redis)
        self.audit = AuditService(session)
        self.redis = redis

    # ------------------------------------------------------------------
    # Brute-Force Protection Helpers
    # ------------------------------------------------------------------
    async def _check_brute_force(self, email: str, ip_address: str = None) -> None:
        """
        Checks if the account is locked due to too many failed login attempts.
        Uses Redis counter with TTL for automatic unlock.
        """
        try:
            lockout_key = f"lockout:{email}"
            if await self.redis.exists(lockout_key):
                ttl = await self.redis.ttl(lockout_key)
                logger.warning("Login attempt on locked account", extra={"email": email, "ip": ip_address})
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Account temporarily locked due to too many failed attempts. Try again in {ttl} seconds.",
                    headers={"Retry-After": str(ttl)},
                )
        except RedisError as exc:
            logger.error("Redis error checking lockout", extra={"error": str(exc)})
            # Fail open — don't lock out legitimate users if Redis is down

    async def _record_failed_login(self, email: str, ip_address: str = None) -> None:
        """
        Increments the failed login counter. Locks the account after
        MAX_FAILED_LOGINS attempts.
        """
        try:
            counter_key = f"failed_login:{email}"
            count = await self.redis.incr(counter_key)

            if count == 1:
                await self.redis.expire(counter_key, LOCKOUT_TTL)

            if count >= MAX_FAILED_LOGINS:
                await self.redis.setex(f"lockout:{email}", LOCKOUT_TTL, "1")
                await self.redis.delete(counter_key)
                logger.warning(
                    "Account locked after too many failed attempts",
                    extra={"email": email, "attempts": count},
                )
                await self.audit.log(
                    action=ACCOUNT_LOCKED,
                    ip_address=ip_address,
                    metadata_info={"email": email, "failed_attempts": count},
                )
        except RedisError as exc:
            logger.error("Redis error recording failed login", extra={"error": str(exc)})

    async def _clear_failed_logins(self, email: str) -> None:
        """Resets the failed login counter after a successful login."""
        try:
            await self.redis.delete(f"failed_login:{email}")
        except RedisError:
            pass

    # ------------------------------------------------------------------
    # Signup
    # ------------------------------------------------------------------
    async def signup(self, user_in: UserCreate, ip_address: str = None) -> User:
        """
        Registers a new user, generates a verification OTP, and queues
        a verification email via Celery.
        """
        existing_user = await self.user_repo.get_by_email(user_in.email)
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        try:
            user = await self.user_repo.create(user_in)
        except IntegrityError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        # Audit: signup
        await self.audit.log(
            action=SIGNUP,
            user_id=user.id,
            ip_address=ip_address,
            metadata_info={"email": user.email},
        )

        # Generate and store hashed OTP in Redis
        try:
            otp = generate_otp()
            hashed_otp = get_password_hash(otp)
            await self.redis.setex(f"verify:{user.id}", OTP_TTL, hashed_otp)
        except RedisError as exc:
            logger.error("Redis error storing OTP", extra={"user_id": str(user.id), "error": str(exc)})
            logger.warning("User created but verification OTP could not be stored", extra={"user_id": str(user.id)})
            return user

        try:
            from app.workers.tasks import send_verification_email
            send_verification_email.delay(user.email, otp)
            logger.info("Verification email queued", extra={"user_id": str(user.id), "email": user.email})
        except Exception as exc:
            logger.error("Failed to queue verification email", extra={"user_id": str(user.id), "error": str(exc)})

        return user

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------
    async def login(
        self,
        email: str,
        password: str,
        device_info: str = None,
        ip_address: str = None,
    ) -> dict:
        """
        Authenticates a user with email/password, creates a session,
        and returns access + refresh tokens.
        Includes brute-force protection via Redis counters.
        """
        # Check brute-force lockout BEFORE any DB lookup
        await self._check_brute_force(email, ip_address)

        user = await self.user_repo.get_by_email(email)
        if not user or not user.hashed_password:
            await self._record_failed_login(email, ip_address)
            await self.audit.log(
                action=LOGIN_FAILED,
                ip_address=ip_address,
                metadata_info={"email": email, "reason": "user_not_found"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not verify_password(password, user.hashed_password):
            await self._record_failed_login(email, ip_address)
            await self.audit.log(
                action=LOGIN_FAILED,
                user_id=user.id,
                ip_address=ip_address,
                metadata_info={"email": email, "reason": "wrong_password"},
            )
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
            )

        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated. Contact support.",
            )

        # Clear failed login counter on success
        await self._clear_failed_logins(email)

        access_token = self.token_service.create_access_token(user.id)
        refresh_token_data = self.token_service.create_refresh_token(user.id)

        await self.session_service.create_session(
            user_id=user.id,
            refresh_token=refresh_token_data["token"],
            expires_at=refresh_token_data["exp"],
            device_info=device_info,
            ip_address=ip_address,
        )

        # Audit: successful login
        await self.audit.log(
            action=LOGIN,
            user_id=user.id,
            ip_address=ip_address,
            metadata_info={"device": device_info},
        )

        logger.info("User logged in", extra={"user_id": str(user.id), "ip": ip_address})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_data["token"],
            "token_type": "bearer",
        }

    # ------------------------------------------------------------------
    # Token Refresh (Rotation)
    # ------------------------------------------------------------------
    async def refresh_token(
        self,
        refresh_token: str,
        device_info: str = None,
        ip_address: str = None,
    ) -> dict:
        """
        Validates the refresh token, rotates it (old one is blacklisted,
        new one is issued), and creates a fresh session.
        """
        payload = self.token_service.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token",
            )

        user_id = payload.get("sub")
        jti = payload.get("jti")
        exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)

        if await self.session_service.is_blacklisted(jti):
            logger.warning("Blacklisted refresh token used", extra={"jti": jti, "user_id": user_id})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has been revoked",
            )

        active_sessions = await self.session_service.session_repo.get_active_sessions_for_user(user_id)
        current_session = None
        for sess in active_sessions:
            if verify_password(refresh_token, sess.refresh_token_hash):
                current_session = sess
                break

        if not current_session:
            logger.warning("Refresh token does not match any active session", extra={"user_id": user_id})
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Session not found or revoked",
            )

        time_remaining = exp - datetime.now(timezone.utc)
        await self.session_service.blacklist_token(jti, time_remaining)
        await self.session_service.session_repo.revoke(current_session)

        access_token = self.token_service.create_access_token(user_id)
        new_refresh_data = self.token_service.create_refresh_token(user_id)

        await self.session_service.create_session(
            user_id=user_id,
            refresh_token=new_refresh_data["token"],
            expires_at=new_refresh_data["exp"],
            device_info=device_info,
            ip_address=ip_address,
        )

        logger.info("Token rotated", extra={"user_id": user_id, "ip": ip_address})

        return {
            "access_token": access_token,
            "refresh_token": new_refresh_data["token"],
            "token_type": "bearer",
        }

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------
    async def logout(self, refresh_token: str, user_id_hint: str = None, ip_address: str = None) -> None:
        """
        Blacklists the refresh token and revokes the matching session.
        Silently ignores invalid tokens — logout should never fail.
        """
        payload = self.token_service.decode_token(refresh_token)
        if not payload or payload.get("type") != "refresh":
            return

        user_id = payload.get("sub")
        jti = payload.get("jti")
        exp = datetime.fromtimestamp(payload.get("exp"), tz=timezone.utc)

        time_remaining = exp - datetime.now(timezone.utc)
        if time_remaining.total_seconds() > 0:
            await self.session_service.blacklist_token(jti, time_remaining)

        try:
            active_sessions = await self.session_service.session_repo.get_active_sessions_for_user(user_id)
            for sess in active_sessions:
                if verify_password(refresh_token, sess.refresh_token_hash):
                    await self.session_service.session_repo.revoke(sess)
                    break
        except SQLAlchemyError as exc:
            logger.error("DB error during logout session revocation", extra={"user_id": user_id, "error": str(exc)})

        await self.audit.log(action=LOGOUT, user_id=user_id, ip_address=ip_address)
        logger.info("User logged out", extra={"user_id": user_id})

    # ------------------------------------------------------------------
    # Email Verification
    # ------------------------------------------------------------------
    async def verify_email(self, email: str, otp: str, ip_address: str = None) -> None:
        """
        Verifies a user's email by validating the OTP stored in Redis.
        Deletes the OTP on success to prevent reuse.
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found",
            )

        if user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already verified",
            )

        try:
            stored_hash = await self.redis.get(f"verify:{user.id}")
        except RedisError as exc:
            logger.error("Redis error reading OTP", extra={"user_id": str(user.id), "error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        if not stored_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="OTP expired or not found. Please request a new one.",
            )

        if not verify_password(otp, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid OTP",
            )

        try:
            await self.redis.delete(f"verify:{user.id}")
        except RedisError:
            pass

        user.is_verified = True
        await self.user_repo.update(user)

        await self.audit.log(action=EMAIL_VERIFIED, user_id=user.id, ip_address=ip_address)
        logger.info("Email verified", extra={"user_id": str(user.id)})

    # ------------------------------------------------------------------
    # Forgot Password
    # ------------------------------------------------------------------
    async def forgot_password(self, email: str, ip_address: str = None) -> None:
        """
        Generates a password reset token and queues a reset email.
        Always returns success to prevent email enumeration.
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            return

        try:
            cooldown_key = f"email_cooldown:{user.id}"
            if await self.redis.exists(cooldown_key):
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Please wait before requesting another email",
                )

            token = generate_reset_token()
            hashed_token = get_password_hash(token)
            await self.redis.setex(f"reset:{user.id}", RESET_TOKEN_TTL, hashed_token)
            await self.redis.setex(cooldown_key, EMAIL_COOLDOWN_TTL, "1")
        except RedisError as exc:
            logger.error("Redis error in forgot_password", extra={"user_id": str(user.id), "error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        await self.audit.log(
            action=PASSWORD_RESET_REQUESTED,
            user_id=user.id,
            ip_address=ip_address,
        )

        try:
            from app.workers.tasks import send_reset_email
            send_reset_email.delay(user.email, token)
            logger.info("Password reset email queued", extra={"user_id": str(user.id)})
        except Exception as exc:
            logger.error("Failed to queue reset email", extra={"user_id": str(user.id), "error": str(exc)})

    # ------------------------------------------------------------------
    # Reset Password
    # ------------------------------------------------------------------
    async def reset_password(self, email: str, token: str, new_password: str, ip_address: str = None) -> None:
        """
        Validates the reset token, updates the password, and revokes
        ALL active sessions to force re-login on every device.
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid request",
            )

        try:
            stored_hash = await self.redis.get(f"reset:{user.id}")
        except RedisError as exc:
            logger.error("Redis error reading reset token", extra={"user_id": str(user.id), "error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

        if not stored_hash:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Token expired or not found",
            )

        if not verify_password(token, stored_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid token",
            )

        try:
            active_sessions = await self.session_service.session_repo.get_active_sessions_for_user(user.id)
            for sess in active_sessions:
                await self.session_service.session_repo.revoke(sess)
            logger.info(
                "All sessions revoked for password reset",
                extra={"user_id": str(user.id), "sessions_revoked": len(active_sessions)},
            )
        except SQLAlchemyError as exc:
            logger.error("DB error revoking sessions during password reset", extra={"error": str(exc)})

        user.hashed_password = get_password_hash(new_password)
        await self.user_repo.update(user)

        try:
            await self.redis.delete(f"reset:{user.id}")
        except RedisError:
            pass

        await self.audit.log(
            action=PASSWORD_RESET_COMPLETED,
            user_id=user.id,
            ip_address=ip_address,
        )
        logger.info("Password reset successful", extra={"user_id": str(user.id)})
