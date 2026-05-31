"""
User Repository — Database operations for User records.

All methods include proper exception handling with transaction rollback
to prevent inconsistent database state on failures.
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from app.models.user import User
from app.schemas.user import UserCreate
from app.utils.security import get_password_hash
from app.utils.logging import get_logger
from typing import Optional

logger = get_logger(__name__)


class UserRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        try:
            result = await self.session.execute(select(User).where(User.email == email))
            return result.scalars().first()
        except SQLAlchemyError as exc:
            logger.error("DB error fetching user by email", extra={"email": email, "error": str(exc)})
            raise

    async def get_by_id(self, user_id: str) -> Optional[User]:
        try:
            result = await self.session.execute(select(User).where(User.id == user_id))
            return result.scalars().first()
        except SQLAlchemyError as exc:
            logger.error("DB error fetching user by id", extra={"user_id": str(user_id), "error": str(exc)})
            raise

    async def get_by_username(self, username: str) -> Optional[User]:
        """Fetch a user by their unique username (case-insensitive — usernames are stored lowercase)."""
        try:
            result = await self.session.execute(
                select(User).where(User.username == username.lower())
            )
            return result.scalars().first()
        except SQLAlchemyError as exc:
            logger.error("DB error fetching user by username", extra={"username": username, "error": str(exc)})
            raise

    async def create(self, user_in: UserCreate) -> User:
        try:
            db_user = User(
                email=user_in.email,
                username=user_in.username,
                hashed_password=get_password_hash(user_in.password),
                full_name=user_in.full_name,
                phone_number=user_in.phone_number,
                date_of_birth=user_in.date_of_birth,
            )
            self.session.add(db_user)
            await self.session.commit()
            await self.session.refresh(db_user)
            logger.info("User created", extra={"user_id": str(db_user.id), "email": db_user.email})
            return db_user
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning("Duplicate key on user creation", extra={"email": user_in.email, "error": str(exc)})
            raise
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("DB error creating user", extra={"email": user_in.email, "error": str(exc)})
            raise

    async def update(self, user: User) -> User:
        try:
            self.session.add(user)
            await self.session.commit()
            await self.session.refresh(user)
            logger.info("User updated", extra={"user_id": str(user.id)})
            return user
        except IntegrityError as exc:
            await self.session.rollback()
            logger.warning("Integrity error updating user", extra={"user_id": str(user.id), "error": str(exc)})
            raise
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("DB error updating user", extra={"user_id": str(user.id), "error": str(exc)})
            raise

    async def delete(self, user: User) -> None:
        try:
            await self.session.delete(user)
            await self.session.commit()
            logger.info("Deleted user record", extra={"user_id": str(user.id)})
        except SQLAlchemyError as exc:
            await self.session.rollback()
            logger.error("DB error deleting user", extra={"user_id": str(user.id), "error": str(exc)})
            raise
