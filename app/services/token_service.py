"""
Token Service — JWT creation and validation.

All token creation includes a unique JTI (JWT ID) for blacklisting support.
Access tokens are short-lived (15 min), refresh tokens are long-lived (7 days).
"""
from datetime import datetime, timedelta, timezone
from typing import Optional
import jwt
from uuid import uuid4
from app.config import settings
from app.utils.logging import get_logger

logger = get_logger(__name__)


class TokenService:
    @staticmethod
    def create_access_token(user_id: str) -> str:
        """Creates a short-lived access token (15 min default)."""
        expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        jti = str(uuid4())
        to_encode = {
            "sub": str(user_id),
            "type": "access",
            "exp": expire,
            "jti": jti,
        }
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.debug("Access token created", extra={"user_id": str(user_id), "jti": jti})
        return encoded_jwt

    @staticmethod
    def create_refresh_token(user_id: str) -> dict:
        """
        Creates a long-lived refresh token (7 days default).
        
        Returns a dict with the token string, JTI, and expiry
        because the caller needs these for session record creation.
        """
        expire = datetime.now(timezone.utc) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
        jti = str(uuid4())
        to_encode = {
            "sub": str(user_id),
            "type": "refresh",
            "exp": expire,
            "jti": jti,
        }
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        logger.debug("Refresh token created", extra={"user_id": str(user_id), "jti": jti})
        return {"token": encoded_jwt, "jti": jti, "exp": expire}

    @staticmethod
    def decode_token(token: str) -> Optional[dict]:
        """
        Decodes and validates a JWT token.
        
        Returns the payload dict on success, or None if the token
        is expired, tampered with, or otherwise invalid.
        """
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            return payload
        except jwt.ExpiredSignatureError:
            logger.debug("Token decode failed: expired")
            return None
        except jwt.InvalidTokenError as exc:
            logger.debug("Token decode failed", extra={"error": str(exc)})
            return None
