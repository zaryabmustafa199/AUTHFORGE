from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from .user import UserResponse

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenData(BaseModel):
    user_id: Optional[str] = None
    email: Optional[str] = None

class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(..., min_length=8, max_length=72)

class SignupResponse(BaseModel):
    user: UserResponse
    message: str = "User created successfully. Please verify your email."

class VerifyEmailRequest(BaseModel):
    email: EmailStr
    otp: str = Field(..., min_length=6, max_length=6)

class ForgotPasswordRequest(BaseModel):
    email: EmailStr

class ResetPasswordRequest(BaseModel):
    email: EmailStr
    token: str
    new_password: str = Field(..., min_length=8, max_length=72)

class MessageResponse(BaseModel):
    message: str
