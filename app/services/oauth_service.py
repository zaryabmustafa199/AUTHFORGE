"""
OAuth Service — Business logic for Google OAuth authentication.

Handles the OAuth flow:
1. Generate the Google consent URL → user clicks "Login with Google"
2. Google redirects back with an authorization code
3. We exchange the code for user info (email, name, Google ID)
4. Create or link the user account and issue JWT tokens

Edge cases handled:
- Existing user with password-based login → links Google account
- Existing user already linked to Google → logs in directly
- Brand new user → creates account with is_verified=True (Google verified)
"""
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from authlib.integrations.httpx_client import AsyncOAuth2Client
from httpx import HTTPStatusError

from app.repositories.user_repo import UserRepository
from app.services.token_service import TokenService
from app.services.session_service import SessionService
from app.services.audit_service import AuditService, SIGNUP, LOGIN
from app.config import settings
from app.utils.logging import get_logger
from typing import Optional

logger = get_logger(__name__)

# Google OAuth endpoints
GOOGLE_AUTHORIZE_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"


class OAuthService:
    def __init__(self, session: AsyncSession, redis: Redis):
        self.user_repo = UserRepository(session)
        self.token_service = TokenService()
        self.session_service = SessionService(session, redis)
        self.audit = AuditService(session)

    # ------------------------------------------------------------------
    # Step 1: Build the Google consent URL
    # ------------------------------------------------------------------
    def get_google_auth_url(self) -> str:
        """
        Generates the Google OAuth consent screen URL.
        The user's browser is redirected here to grant permission.
        """
        if not settings.GOOGLE_CLIENT_ID:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth is not configured. Set GOOGLE_CLIENT_ID in .env",
            )

        client = AsyncOAuth2Client(
            client_id=settings.GOOGLE_CLIENT_ID,
            redirect_uri=settings.GOOGLE_REDIRECT_URI,
            scope="openid email profile",
        )
        uri, _ = client.create_authorization_url(GOOGLE_AUTHORIZE_URL)
        return uri

    # ------------------------------------------------------------------
    # Step 2: Handle the callback — exchange code for tokens + user info
    # ------------------------------------------------------------------
    async def google_callback(
        self,
        code: str,
        device_info: Optional[str] = None,
        ip_address: Optional[str] = None,
    ) -> dict:
        """
        Called when Google redirects back to our app with an authorization code.

        Flow:
        1. Exchange the code for a Google access token
        2. Use the access token to get the user's Google profile
        3. Find or create the user in our database
        4. Issue our own JWT tokens
        """
        if not settings.GOOGLE_CLIENT_ID or not settings.GOOGLE_CLIENT_SECRET:
            raise HTTPException(
                status_code=status.HTTP_501_NOT_IMPLEMENTED,
                detail="Google OAuth is not configured",
            )

        # Exchange authorization code for tokens
        try:
            client = AsyncOAuth2Client(
                client_id=settings.GOOGLE_CLIENT_ID,
                client_secret=settings.GOOGLE_CLIENT_SECRET,
                redirect_uri=settings.GOOGLE_REDIRECT_URI,
            )
            token_response = await client.fetch_token(
                GOOGLE_TOKEN_URL,
                code=code,
            )
        except Exception as exc:
            logger.error("Failed to exchange Google auth code", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to authenticate with Google. Please try again.",
            )

        # Fetch user info from Google
        try:
            resp = await client.get(GOOGLE_USERINFO_URL)
            resp.raise_for_status()
            google_user = resp.json()
        except Exception as exc:
            logger.error("Failed to fetch Google user info", extra={"error": str(exc)})
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to retrieve user information from Google.",
            )

        google_email = google_user.get("email")
        google_id = google_user.get("sub")
        google_name = google_user.get("name")

        if not google_email or not google_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Google did not provide email or user ID",
            )

        logger.info("Google user info received", extra={"email": google_email, "google_id": google_id})

        # Find or create user
        user = await self._find_or_create_user(
            email=google_email,
            google_id=google_id,
            full_name=google_name,
            ip_address=ip_address,
        )

        # Issue tokens
        access_token = self.token_service.create_access_token(user.id)
        refresh_token_data = self.token_service.create_refresh_token(user.id)

        await self.session_service.create_session(
            user_id=user.id,
            refresh_token=refresh_token_data["token"],
            expires_at=refresh_token_data["exp"],
            device_info=device_info,
            ip_address=ip_address,
        )

        await self.audit.log(
            action=LOGIN,
            user_id=user.id,
            ip_address=ip_address,
            metadata_info={"method": "google_oauth", "google_id": google_id},
        )

        logger.info("Google OAuth login successful", extra={"user_id": str(user.id)})

        return {
            "access_token": access_token,
            "refresh_token": refresh_token_data["token"],
            "token_type": "bearer",
        }

    # ------------------------------------------------------------------
    # Internal: Find existing user or create a new one
    # ------------------------------------------------------------------
    async def _find_or_create_user(
        self,
        email: str,
        google_id: str,
        full_name: Optional[str] = None,
        ip_address: Optional[str] = None,
    ):
        """
        Three scenarios:
        1. User exists with this Google ID → login directly
        2. User exists with this email (password login) → link Google account
        3. No user with this email → create new OAuth user
        """
        from app.schemas.user import UserCreate

        # Scenario 1 & 2: Check if user exists by email
        existing_user = await self.user_repo.get_by_email(email)

        if existing_user:
            if existing_user.oauth_provider == "google" and existing_user.oauth_provider_id == google_id:
                # Scenario 1: Already linked — just log in
                if not existing_user.is_active:
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail="Account is deactivated. Contact support.",
                    )
                return existing_user

            if existing_user.oauth_provider is None:
                # Scenario 2: Existing password user — link Google account
                existing_user.oauth_provider = "google"
                existing_user.oauth_provider_id = google_id
                existing_user.is_verified = True  # Google-verified email
                if not existing_user.full_name and full_name:
                    existing_user.full_name = full_name
                await self.user_repo.update(existing_user)
                logger.info("Linked Google account to existing user", extra={"user_id": str(existing_user.id)})
                return existing_user

            # User already linked to a DIFFERENT provider — edge case
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This email is already associated with another authentication method.",
            )

        # Scenario 3: Brand new user — create from Google info
        from app.models.user import User
        new_user = User(
            email=email,
            full_name=full_name,
            hashed_password=None,  # No password for OAuth users
            oauth_provider="google",
            oauth_provider_id=google_id,
            is_verified=True,  # Google verified their email
        )

        try:
            from sqlalchemy.exc import IntegrityError
            self.user_repo.session.add(new_user)
            await self.user_repo.session.commit()
            await self.user_repo.session.refresh(new_user)
        except IntegrityError:
            await self.user_repo.session.rollback()
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered",
            )

        await self.audit.log(
            action=SIGNUP,
            user_id=new_user.id,
            ip_address=ip_address,
            metadata_info={"method": "google_oauth", "email": email},
        )

        logger.info("New user created via Google OAuth", extra={"user_id": str(new_user.id), "email": email})
        return new_user
