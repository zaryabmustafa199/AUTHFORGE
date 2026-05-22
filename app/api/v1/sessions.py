from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from redis.asyncio import Redis
from app.api.deps import get_db, get_current_user
from app.redis import get_redis
from app.schemas.session import SessionResponse
from app.services.session_service import SessionService
from app.models.user import User
from typing import List
from uuid import UUID

router = APIRouter()

@router.get("/", response_model=List[SessionResponse])
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    session_service = SessionService(db, redis)
    return await session_service.session_repo.get_active_sessions_for_user(current_user.id)

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def revoke_session(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    redis: Redis = Depends(get_redis),
    current_user: User = Depends(get_current_user)
):
    session_service = SessionService(db, redis)
    await session_service.revoke_session(session_id, current_user.id)
    return None
