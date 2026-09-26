from datetime import datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, field_validator

# bcrypt only ever looks at the first 72 bytes of a password. Up to bcrypt
# 4.x, anything past that was silently truncated. Starting with bcrypt 5.0,
# hashpw() raises ValueError instead — without this check, a long password
# would crash register/login with an unhandled 500 instead of a clean 422.
MAX_PASSWORD_BYTES = 72


def _validate_password_length(value: str) -> str:
    if len(value.encode("utf-8")) > MAX_PASSWORD_BYTES:
        raise ValueError(f"Password must be {MAX_PASSWORD_BYTES} bytes or fewer")
    return value


class UserBase(BaseModel):
    email: EmailStr
    username: str


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        return _validate_password_length(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("password")
    @classmethod
    def validate_password_length(cls, value: str) -> str:
        return _validate_password_length(value)


class UserUpdate(BaseModel):
    username: Optional[str] = None


# Deliberately a separate endpoint/schema from UserUpdate (android#87) rather
# than folding password fields into it — changing the password is a more
# security-sensitive operation than a plain profile field edit, and keeping
# it separate avoids ambiguity about what should happen if a combined
# request had a bad current_password alongside an otherwise-valid username
# change. current_password is required: the user's JWT session alone proves
# they're logged in right now, not that they still know the password (e.g. a
# stolen/still-valid token) — re-checking it here is what stops someone in
# that position from locking the real owner out.
class PasswordChange(BaseModel):
    current_password: str
    new_password: str

    @field_validator("new_password")
    @classmethod
    def validate_new_password_length(cls, value: str) -> str:
        return _validate_password_length(value)


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
