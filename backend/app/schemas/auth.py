from __future__ import annotations

import uuid
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=200)
    preferred_language: Literal["ar", "en"] = "en"
    timezone: str = "Asia/Dubai"
    intake_id: uuid.UUID | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    user_id: uuid.UUID
    email: str
    role: str
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = 900
    requires_totp: bool = False


class RefreshRequest(BaseModel):
    refresh_token: str


class RefreshResponse(BaseModel):
    access_token: str
    refresh_token: str
    expires_in: int = 900


class GoogleCallbackResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    is_new_user: bool


class TOTPSetupResponse(BaseModel):
    secret: str
    qr_uri: str
    backup_codes: list[str]


class TOTPVerifyRequest(BaseModel):
    # 6 chars: TOTP codes. 9 chars: backup codes displayed as "XXXX-YYYY" (hyphen included).
    code: str = Field(min_length=6, max_length=9)


class TOTPVerifyResponse(BaseModel):
    verified: bool
    access_token: str


class DeleteRequestResponse(BaseModel):
    message: str
    scheduled_deletion_at: str
