from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.favorite_place import FavoritePlace
from ..models.user import User
from ..schemas.favorite_place import FavoritePlaceCreate, FavoritePlaceRead

router = APIRouter(prefix="/api/v1/favorite-places", tags=["favorite-places"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

# One list per user — no type distinction (origin/destination/stop), the
# app treats every favorite as usable for any of those fields.


@router.post("", response_model=FavoritePlaceRead, status_code=status.HTTP_201_CREATED)
def create_favorite_place(
    favorite_in: FavoritePlaceCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> FavoritePlace:
    favorite = FavoritePlace(user_id=current_user.id, **favorite_in.model_dump())
    db.add(favorite)
    db.commit()
    db.refresh(favorite)
    return favorite


@router.get("", response_model=List[FavoritePlaceRead])
def list_favorite_places(db: DbDep, current_user: CurrentUserDep) -> list[FavoritePlace]:
    return (
        db.query(FavoritePlace)
        .filter(FavoritePlace.user_id == current_user.id)
        .order_by(FavoritePlace.name)
        .all()
    )


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_favorite_place(favorite_id: str, db: DbDep, current_user: CurrentUserDep) -> None:
    favorite = (
        db.query(FavoritePlace)
        .filter(FavoritePlace.id == favorite_id, FavoritePlace.user_id == current_user.id)
        .first()
    )
    if favorite is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Favorite place not found")
    db.delete(favorite)
    db.commit()
