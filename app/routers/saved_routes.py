from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.saved_route import SavedRoute
from ..models.user import User
from ..schemas.saved_route import SavedRouteCreate, SavedRouteRead, SavedRouteUpdate
from ..services.trip_stats_service import haversine_distance_km

router = APIRouter(prefix="/api/v1/saved-routes", tags=["saved-routes"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

# How far a trip's origin and destination may each be from a saved route's
# for that route to be offered. Loose on purpose: "Casa" picked from
# favorites and "Casa" confirmed on the map land a few dozen meters apart.
SAVED_ROUTE_MATCH_METERS = 500.0


def _get_owned_saved_route(db: Session, saved_route_id: str, user_id: str) -> SavedRoute:
    saved_route = (
        db.query(SavedRoute)
        .filter(SavedRoute.id == saved_route_id, SavedRoute.user_id == user_id)
        .first()
    )
    if saved_route is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Saved route not found")
    return saved_route


def _is_near(lat_a: float, lng_a: float, lat_b: float, lng_b: float) -> bool:
    return haversine_distance_km(lat_a, lng_a, lat_b, lng_b) * 1000 <= SAVED_ROUTE_MATCH_METERS


@router.post("", response_model=SavedRouteRead, status_code=status.HTTP_201_CREATED)
def create_saved_route(
    saved_route_in: SavedRouteCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> SavedRoute:
    saved_route = SavedRoute(user_id=current_user.id, **saved_route_in.model_dump())
    db.add(saved_route)
    db.commit()
    db.refresh(saved_route)
    return saved_route


@router.get("", response_model=List[SavedRouteRead])
def list_saved_routes(
    db: DbDep,
    current_user: CurrentUserDep,
    origin_lat: Optional[float] = None,
    origin_lng: Optional[float] = None,
    destination_lat: Optional[float] = None,
    destination_lng: Optional[float] = None,
) -> list[SavedRoute]:
    """All of the user's saved routes, or, when an origin and destination are
    given, only those that start and end near them (what the Create trip
    screen offers for the trip being planned).
    """
    saved_routes = (
        db.query(SavedRoute)
        .filter(SavedRoute.user_id == current_user.id)
        .order_by(SavedRoute.name)
        .all()
    )
    coords = (origin_lat, origin_lng, destination_lat, destination_lng)
    if all(c is None for c in coords):
        return saved_routes
    if any(c is None for c in coords):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="Filtering needs origin_lat, origin_lng, destination_lat and destination_lng",
        )
    # A user has a handful of saved routes at most, so filtering in Python
    # is simpler than a geographic query and just as fast.
    return [
        r
        for r in saved_routes
        if _is_near(r.origin_lat, r.origin_lng, origin_lat, origin_lng)
        and _is_near(r.destination_lat, r.destination_lng, destination_lat, destination_lng)
    ]


@router.get("/{saved_route_id}", response_model=SavedRouteRead)
def get_saved_route(saved_route_id: str, db: DbDep, current_user: CurrentUserDep) -> SavedRoute:
    return _get_owned_saved_route(db, saved_route_id, current_user.id)


@router.patch("/{saved_route_id}", response_model=SavedRouteRead)
def update_saved_route(
    saved_route_id: str,
    saved_route_in: SavedRouteUpdate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> SavedRoute:
    saved_route = _get_owned_saved_route(db, saved_route_id, current_user.id)
    for field, value in saved_route_in.model_dump(exclude_unset=True, exclude_none=True).items():
        setattr(saved_route, field, value)
    db.add(saved_route)
    db.commit()
    db.refresh(saved_route)
    return saved_route


@router.delete("/{saved_route_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_saved_route(saved_route_id: str, db: DbDep, current_user: CurrentUserDep) -> None:
    saved_route = _get_owned_saved_route(db, saved_route_id, current_user.id)
    db.delete(saved_route)
    db.commit()
