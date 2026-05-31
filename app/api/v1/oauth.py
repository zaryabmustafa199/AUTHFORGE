"""
OAuth Routes — Google OAuth login endpoints.

Two endpoints:
1. GET /oauth/google — redirects user to Google consent screen
2. GET /oauth/google/callback — handles the redirect back from Google
"""
from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis

from app.api.deps import get_db
from app.redis import get_redis
from app.services.oauth_service import OAuthService
from app.config import settings

router = APIRouter()


@router.get("/google")
async def google_login():
    """
    Redirects the user to Google's OAuth consent screen.
    After the user grants permission, Google redirects back to /callback.
    """
    oauth_service = OAuthService.__new__(OAuthService)
    auth_url = oauth_service.get_google_auth_url()
    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_callback(
    request: Request,
    code: str = Query(..., description="Authorization code from Google"),
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
):
    """
    Handles the redirect from Google after the user grants permission.
    Exchanges the authorization code for user info, creates/links the user,
    and returns JWT tokens.
    """
    oauth_service = OAuthService(db, redis)
    device_info = request.headers.get("user-agent", "Unknown")
    ip_address = request.client.host if request.client else None
    
    tokens = await oauth_service.google_callback(code, device_info, ip_address)
    
    redirect_url = f"{settings.FRONTEND_URL}/login?access_token={tokens['access_token']}&refresh_token={tokens['refresh_token']}"
    return RedirectResponse(url=redirect_url)
