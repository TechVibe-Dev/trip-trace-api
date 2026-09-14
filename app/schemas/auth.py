from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

# bcrypt only ever looks at the first 72 bytes of a password. Up to bcrypt
# 4.x, anything past that was silently truncated. Starting with bcrypt 5.0,
# hashpw() raises ValueError instead — without this check, a long password
# would crash register/login with an unhandled 500 instead of a clean 422.
MAX_PASSWORD_BYTES = 72


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be {MAX_PASSWORD_BYTES} bytes or fewer")
        return value


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
            raise ValueError(f"Password must be {MAX_PASSWORD_BYTES} bytes or fewer")
        return value


class UserUpdate(BaseModel):
    username: Optional[str] = None


class UserRead(UserBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    user_id: Optional[str] = None
