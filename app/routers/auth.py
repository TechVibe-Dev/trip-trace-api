from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.user import User
from ..schemas.auth import Token, UserCreate, UserRead, UserUpdate
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
    user = db.query(User).filter(User.email == form_data.username).first()
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
