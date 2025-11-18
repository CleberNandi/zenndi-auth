from datetime import datetime

from pydantic import EmailStr, Field

from app.shared.schemas.base import BaseSchema

BEARER_TOKEN_TYPE = "bearer"


class UserRegister(BaseSchema):
    nome: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserLogin(BaseSchema):
    email: EmailStr
    password: str


class UserLogin2FA(BaseSchema):
    email: EmailStr
    password: str
    totp_code: str | None = None
    backup_code: str | None = None


class TokenResponse(BaseSchema):
    access_token: str
    refresh_token: str
    token_type: str = BEARER_TOKEN_TYPE
    expires_in: int
    requires_2fa: bool = False


class RefreshTokenRequest(BaseSchema):
    refresh_token: str


class Enable2FARequest(BaseSchema):
    totp_code: str


class Verify2FARequest(BaseSchema):
    totp_code: str | None = None
    backup_code: str | None = None


class PasswordChangeRequest(BaseSchema):
    current_password: str
    new_password: str = Field(..., min_length=8)


class PasswordResetRequest(BaseSchema):
    email: EmailStr


class PasswordResetConfirm(BaseSchema):
    token: str
    new_password: str = Field(..., min_length=8)


class UserProfile(BaseSchema):
    id: int
    nome: str
    email: str
    is_verified: bool
    is_2fa_enabled: bool
    plan: str | None
    last_login: datetime | None
    created_at: datetime


class TwoFactorSetup(BaseSchema):
    secret: str
    qr_code: str
    backup_codes: list[str]


class DeviceInfo(BaseSchema):
    session_id: str
    device_info: str | None
    ip_address: str | None
    user_agent: str | None
    last_activity: datetime
    is_current: bool
