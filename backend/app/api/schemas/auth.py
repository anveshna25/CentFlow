from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class RegisterRequest(BaseModel):
    """Schema for account registration."""

    email: str = Field(..., min_length=5, max_length=255, description="User email address")
    password: str = Field(..., min_length=8, max_length=128, description="Plaintext password")
    display_name: str = Field(..., min_length=2, max_length=100, description="User full name or handle")


class LoginRequest(BaseModel):
    """Schema for email/password authentication."""

    email: str = Field(..., description="User email address")
    password: str = Field(..., description="User password")


class VerifyEmailRequest(BaseModel):
    """Schema to redeem an email verification token."""

    token: str = Field(..., min_length=16, description="Single-use verification token")


class ForgotPasswordRequest(BaseModel):
    """Schema to initiate password recovery."""

    email: str = Field(..., description="Account email address")


class ResetPasswordRequest(BaseModel):
    """Schema to complete password recovery."""

    token: str = Field(..., min_length=16, description="Single-use password reset token")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")


class ChangePasswordRequest(BaseModel):
    """Schema to change password for authenticated user."""

    current_password: str = Field(..., description="Existing plaintext password")
    new_password: str = Field(..., min_length=8, max_length=128, description="New plaintext password")


class UserIdentityResponse(BaseModel):
    """Schema representing a linked identity provider."""

    id: str
    provider: str
    provider_email: Optional[str] = None
    created_at: datetime


class UserResponse(BaseModel):
    """Schema representing an authenticated user profile."""

    id: str
    email: str
    display_name: str
    email_verified: bool
    is_active: bool
    has_password: bool
    identities: list[UserIdentityResponse] = []
    created_at: datetime


class SessionResponse(BaseModel):
    """Schema representing an active user session."""

    id: str
    created_at: datetime
    expires_at: datetime
    last_used_at: datetime
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    is_current: bool = False


class AuthSuccessResponse(BaseModel):
    """Schema for successful authentication response."""

    user: UserResponse
    message: str = "Authenticated successfully"

