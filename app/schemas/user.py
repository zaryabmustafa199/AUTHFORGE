"""
User Schemas — Request/response models for user endpoints.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from uuid import UUID
from datetime import datetime
from typing import Optional, List


class UserBase(BaseModel):
    email: EmailStr
    full_name: Optional[str] = None


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=72)


class UserProfileUpdate(BaseModel):
    """Schema for users updating their own profile. Limited fields."""
    full_name: Optional[str] = Field(None, max_length=100)


class AdminUserUpdate(BaseModel):
    """Schema for admins updating any user. Can change role and active status."""
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class RoleResponse(BaseModel):
    """Embedded role info in user responses."""
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Standard user response — used in most endpoints."""
    id: UUID
    email: EmailStr
    full_name: Optional[str] = None
    is_verified: bool
    is_active: bool
    role_id: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    """Extended user response with role details — used in admin views."""
    role: Optional[RoleResponse] = None
    updated_at: Optional[datetime] = None
    oauth_provider: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users for admin endpoints."""
    users: List[UserDetailResponse]
    total: int
    page: int
    per_page: int
