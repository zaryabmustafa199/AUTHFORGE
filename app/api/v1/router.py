"""
API v1 Router — aggregates all route modules under /api/v1.
"""
from fastapi import APIRouter
from . import auth
from . import sessions
from . import users
from . import oauth

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(oauth.router, prefix="/auth/oauth", tags=["OAuth"])
api_router.include_router(sessions.router, prefix="/sessions", tags=["Sessions"])
api_router.include_router(users.router, prefix="/users", tags=["Users"])
