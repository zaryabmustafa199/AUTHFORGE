"""
User Schemas — Request/response models for user endpoints.

All validators enforce strict production-grade rules:
- username: alphanumeric + underscores only, 3-50 chars, normalized to lowercase
- phone_number: E.164 format (+country_code + digits)
- date_of_birth: minimum age of 13 years
"""
import re
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from uuid import UUID
from datetime import datetime, date
from typing import Optional, List


class UserBase(BaseModel):
    email: EmailStr
    full_name: str = Field(..., min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email_domain(cls, v: str) -> str:
        allowed_domains = ["gmail.com", "yahoo.com", "outlook.com", "hotmail.com"]
        domain = v.split("@")[1].lower()
        if domain not in allowed_domains:
            raise ValueError(f"Email must be from an allowed domain: {', '.join(allowed_domains)}")
        return v


class UserCreate(UserBase):
    username: str = Field(..., min_length=3, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)
    date_of_birth: Optional[date] = None
    password: str = Field(..., min_length=8, max_length=72)

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter")
        if not re.search(r"[0-9]", v):
            raise ValueError("Password must contain at least one number")
        if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", v):
            raise ValueError("Password must contain at least one special character")
        return v

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username may only contain letters, numbers, and underscores"
            )
        return v.lower()

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^\+[1-9]\d{7,14}$", v):
            raise ValueError(
                "Phone number must be in E.164 format (e.g. +923001234567)"
            )
        return v

    @field_validator("date_of_birth")
    @classmethod
    def validate_age(cls, v: Optional[date]) -> Optional[date]:
        if v is not None:
            today = date.today()
            age = today.year - v.year - (
                (today.month, today.day) < (v.month, v.day)
            )
            if age < 13:
                raise ValueError("You must be at least 13 years old to register")
        return v


class UserProfileUpdate(BaseModel):
    """Schema for users updating their own profile."""
    full_name: Optional[str] = Field(None, max_length=100)
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    phone_number: Optional[str] = Field(None, max_length=20)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^[a-zA-Z0-9_]+$", v):
            raise ValueError(
                "Username may only contain letters, numbers, and underscores"
            )
        return v.lower() if v else v

    @field_validator("phone_number")
    @classmethod
    def validate_phone(cls, v: Optional[str]) -> Optional[str]:
        if v and not re.match(r"^\+[1-9]\d{7,14}$", v):
            raise ValueError(
                "Phone number must be in E.164 format (e.g. +923001234567)"
            )
        return v


class AdminUserUpdate(BaseModel):
    """Schema for admins updating any user. Can change role and active/verified status."""
    role_id: Optional[int] = None
    is_active: Optional[bool] = None
    is_verified: Optional[bool] = None


class RoleResponse(BaseModel):
    """Embedded role info in user responses."""
    id: int
    name: str
    permissions: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)


class UserResponse(BaseModel):
    """Standard user response — used in most endpoints."""
    id: UUID
    email: EmailStr
    username: Optional[str] = None
    full_name: Optional[str] = None
    phone_number: Optional[str] = None
    date_of_birth: Optional[date] = None
    is_verified: bool
    is_active: bool
    role_id: int
    role: Optional[RoleResponse] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class UserDetailResponse(UserResponse):
    """Extended user response with full details — used in admin views."""
    updated_at: Optional[datetime] = None
    oauth_provider: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class PaginatedUsersResponse(BaseModel):
    """Paginated list of users for admin endpoints."""
    users: List[UserDetailResponse]
    total: int
    page: int
    per_page: int


class UsernameAvailabilityResponse(BaseModel):
    """Response for the username availability check endpoint."""
    username: str
    available: bool
