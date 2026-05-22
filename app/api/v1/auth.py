"""
Auth Routes — Signup, Login, Token Refresh, Logout,
Email Verification, and Password Reset endpoints.

Rate-limited where appropriate to prevent abuse.
"""
from fastapi import APIRouter, Depends, status, Request, Body
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.api.deps import get_db, get_current_user
from app.redis import get_redis
from app.schemas.auth import (
    SignupResponse, Token, VerifyEmailRequest,
    ForgotPasswordRequest, ResetPasswordRequest, MessageResponse,
)
from app.schemas.user import UserCreate
from app.services.auth_service import AuthService
from app.models.user import User
from app.middleware.rate_limiter import rate_limit
from app.config import settings
from fastapi.security import OAuth2PasswordRequestForm

router = APIRouter()


@router.post("/signup", response_model=SignupResponse, status_code=status.HTTP_201_CREATED)
async def signup(
    request: Request,
    user_in: UserCreate,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _rate=Depends(rate_limit("signup", settings.RATE_LIMIT_SIGNUP, settings.RATE_LIMIT_WINDOW_SECONDS)),
):
    """Register a new user account. Sends a verification OTP to the provided email."""
    auth_service = AuthService(db, redis)
    ip_address = request.client.host if request.client else None
    user = await auth_service.signup(user_in, ip_address=ip_address)
    return {"user": user}


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _rate=Depends(rate_limit("login", settings.RATE_LIMIT_LOGIN, settings.RATE_LIMIT_WINDOW_SECONDS)),
):
    """Authenticate with email/password. Returns access + refresh tokens."""
    auth_service = AuthService(db, redis)
    device_info = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host if request.client else None
    return await auth_service.login(form_data.username, form_data.password, device_info, ip_address)


@router.post("/refresh", response_model=Token)
async def refresh_token(
    request: Request,
    refresh_token: str = Body(..., max_length=2048, embed=True),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Exchange a valid refresh token for a new token pair (rotation)."""
    auth_service = AuthService(db, redis)
    device_info = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host if request.client else None
    return await auth_service.refresh_token(refresh_token, device_info, ip_address)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    refresh_token: str = Body(..., max_length=2048, embed=True),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user),
):
    """Revoke the refresh token and its associated session."""
    auth_service = AuthService(db, redis)
    ip_address = request.client.host if request.client else None
    await auth_service.logout(refresh_token, ip_address=ip_address)
    return None


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    request: Request,
    request_data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Verify a user's email address with the 6-digit OTP sent during signup."""
    auth_service = AuthService(db, redis)
    ip_address = request.client.host if request.client else None
    await auth_service.verify_email(request_data.email, request_data.otp, ip_address=ip_address)
    return {"message": "Email successfully verified"}


@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    request: Request,
    request_data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    _rate=Depends(rate_limit("forgot_password", 3, settings.RATE_LIMIT_WINDOW_SECONDS)),
):
    """Request a password reset email. Always returns success to prevent email enumeration."""
    auth_service = AuthService(db, redis)
    ip_address = request.client.host if request.client else None
    await auth_service.forgot_password(request_data.email, ip_address=ip_address)
    return {"message": "If an account with that email exists, a password reset link has been sent"}


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    request: Request,
    request_data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """Reset password using the token received via email. Revokes all existing sessions."""
    auth_service = AuthService(db, redis)
    ip_address = request.client.host if request.client else None
    await auth_service.reset_password(
        request_data.email, request_data.token, request_data.new_password, ip_address=ip_address,
    )
    return {"message": "Password successfully reset. Please log in with your new password"}
