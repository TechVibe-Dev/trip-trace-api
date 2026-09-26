from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..schemas.auth import PasswordChange, Token, UserCreate, UserRead, UserUpdate
from ..services.auth_service import create_access_token, get_password_hash, verify_password


router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


DbDep = Annotated[Session, Depends(get_db)]


@router.post("/register", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def register(user_in: UserCreate, db: DbDep) -> User:
    existing = (
        db.query(User)
        .filter((User.email == user_in.email) | (User.username == user_in.username))
        .first()
    )
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with that email or username already exists",
        )

    user = User(
        email=user_in.email,
        username=user_in.username,
        password_hash=get_password_hash(user_in.password),
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.post("/login", response_model=Token)
def login(
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
    db: DbDep,
) -> Token:
    # OAuth2PasswordRequestForm's field is always named "username" per spec,
    # regardless of what identifier it actually holds — accept either the
    # user's email or their username here (android#83), same either/or
    # pattern register() already uses to check for existing accounts.
    identifier = form_data.username
    user = (
        db.query(User)
        .filter((User.email == identifier) | (User.username == identifier))
        .first()
    )
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credentials",
        )

    access_token = create_access_token(data={"sub": str(user.id)})
    return Token(access_token=access_token)


@router.get("/me", response_model=UserRead)
def get_me(current_user: Annotated[User, Depends(get_current_user)]) -> User:
    return current_user


@router.put("/me", response_model=UserRead)
def update_me(
    user_update: UserUpdate,
    db: DbDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> User:
    if user_update.username is not None:
        exists = (
            db.query(User)
            .filter(User.username == user_update.username, User.id != current_user.id)
            .first()
        )
        if exists:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="That username is already taken",
            )
        current_user.username = user_update.username

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me/password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    password_change: PasswordChange,
    db: DbDep,
    current_user: Annotated[User, Depends(get_current_user)],
) -> None:
    """Separate from update_me on purpose (android#87) — requires
    current_password even though the caller is already authenticated via
    JWT, since a valid session alone doesn't prove they still know the
    password (e.g. a stolen but not-yet-expired token). Without this check,
    whoever holds that token could lock the real owner out permanently.
    """
    if not verify_password(password_change.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )

    current_user.password_hash = get_password_hash(password_change.new_password)
    db.add(current_user)
    db.commit()
