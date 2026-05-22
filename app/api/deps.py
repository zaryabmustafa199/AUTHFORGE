"""
FastAPI Dependency Injection — shared dependencies for all routes.

Provides database sessions, Redis clients, the authentication
gatekeeper (get_current_user), and the role-based access control
dependency (require_role).
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import selectinload
from sqlalchemy.future import select
from redis.asyncio import Redis
from redis.exceptions import RedisError
from typing import AsyncGenerator, List, Callable

from app.database import async_session_maker
from app.redis import get_redis
from app.services.token_service import TokenService
from app.models.user import User
from app.utils.logging import get_logger

logger = get_logger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v1/auth/login")


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """
    Yields an async database session.
    The session is automatically closed after the request completes.
    """
    async with async_session_maker() as session:
        yield session


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    """
    Authentication gatekeeper — validates the JWT access token,
    checks the Redis blacklist, and loads the user from the database
    with the role relationship eager-loaded.

    Any route that includes `current_user: User = Depends(get_current_user)`
    is automatically protected.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # 1. Decode JWT
    payload = TokenService.decode_token(token)
    if payload is None:
        raise credentials_exception

    # 2. Ensure it's an access token (not a refresh token)
    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # 3. Check Redis blacklist
    jti = payload.get("jti")
    if jti:
        try:
            is_blacklisted = await redis.exists(f"blacklist:{jti}")
            if is_blacklisted:
                logger.info("Blacklisted access token used", extra={"jti": jti})
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token has been revoked",
                    headers={"WWW-Authenticate": "Bearer"},
                )
        except RedisError as exc:
            logger.error("Redis error checking blacklist in get_current_user", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Service temporarily unavailable",
            )

    # 4. Load user from database WITH role eager-loaded
    user_id: str = payload.get("sub")
    if user_id is None:
        raise credentials_exception

    try:
        result = await db.execute(
            select(User)
            .options(selectinload(User.role))
            .where(User.id == user_id)
        )
        user = result.scalars().first()
    except SQLAlchemyError as exc:
        logger.error("DB error loading user in get_current_user", extra={"user_id": user_id, "error": str(exc)})
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable",
        )

    if user is None:
        raise credentials_exception

    # 5. Check if user is active
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )

    return user


def require_role(allowed_roles: List[str]) -> Callable:
    """
    Role-based access control dependency factory.

    Usage in routes:
        @router.get("/admin/users")
        async def list_users(current_user: User = Depends(require_role(["admin"]))):
            ...

    This first authenticates the user (via get_current_user), then
    checks if their role is in the allowed list. Returns 403 if not.
    """
    async def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if not current_user.role:
            logger.warning(
                "User has no role assigned",
                extra={"user_id": str(current_user.id)},
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        if current_user.role.name not in allowed_roles:
            logger.info(
                "Access denied — insufficient role",
                extra={
                    "user_id": str(current_user.id),
                    "user_role": current_user.role.name,
                    "required_roles": allowed_roles,
                },
            )
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )

        return current_user

    return role_checker
