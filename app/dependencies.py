from datetime import datetime, timezone
from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_db
from .models.user import User
from .schemas.auth import TokenData


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def get_current_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    settings = get_settings()
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        user_id: str | None = payload.get("sub")
        if user_id is None:
            raise credentials_exception
        token_data = TokenData(user_id=user_id)
        token_issued_at = payload.get("iat")
    except JWTError:
        raise credentials_exception

    user = db.query(User).filter(User.id == token_data.user_id).first()
    if user is None:
        raise credentials_exception

    # Stateless JWTs are never stored server-side, so this "iat vs
    # password_changed_at" check is the only way to reject a token issued
    # before the password was last changed, even though it hasn't hit its
    # own "exp" yet. Applies to every token for this user everywhere
    # (frontend, Android, /docs) — there's no per-device concept to spare
    # any of them, including the one that made the change itself.
    if user.password_changed_at is not None and token_issued_at is not None:
        issued_at = datetime.fromtimestamp(token_issued_at, tz=timezone.utc)
        if issued_at < user.password_changed_at:
            raise credentials_exception

    return user
