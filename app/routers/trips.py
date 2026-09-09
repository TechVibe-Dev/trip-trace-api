from typing import Annotated, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from ..database import get_db
from ..dependencies import get_current_user
from ..models.gps_point import GpsPoint
from ..models.stop import Stop
from ..models.trip import Trip
from ..models.user import User
from ..schemas.trip import (
    GpsPointCreate,
    GpsPointRead,
    StopCreate,
    StopRead,
    StopUpdate,
    TripCreate,
    TripRead,
    TripSegmentRead,
    TripUpdate,
)
from ..services.trip_stats_service import compute_trip_segments, compute_trip_stats

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]


def _get_owned_trip(db: Session, trip_id: str, user_id: str) -> Trip:
    trip = db.query(Trip).filter(Trip.id == trip_id, Trip.user_id == user_id).first()
    if trip is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Trip not found")
    return trip


# --- Trips ---


@router.post("", response_model=TripRead, status_code=status.HTTP_201_CREATED)
def create_trip(trip_in: TripCreate, db: DbDep, current_user: CurrentUserDep) -> Trip:
    trip = Trip(user_id=current_user.id, **trip_in.model_dump())
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("", response_model=List[TripRead])
def list_trips(
    db: DbDep,
    current_user: CurrentUserDep,
    status_filter: Optional[str] = None,
) -> list[Trip]:
    query = db.query(Trip).filter(Trip.user_id == current_user.id)
    if status_filter:
        query = query.filter(Trip.status == status_filter)
    return query.order_by(Trip.created_at.desc()).all()


@router.get("/{trip_id}", response_model=TripRead)
def get_trip(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> Trip:
    return _get_owned_trip(db, trip_id, current_user.id)


@router.patch("/{trip_id}", response_model=TripRead)
def update_trip(
    trip_id: str,
    trip_in: TripUpdate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Trip:
    trip = _get_owned_trip(db, trip_id, current_user.id)
    for field, value in trip_in.model_dump(exclude_unset=True).items():
        setattr(trip, field, value)
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.delete("/{trip_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_trip(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> None:
    trip = _get_owned_trip(db, trip_id, current_user.id)
    db.delete(trip)
    db.commit()


@router.post("/{trip_id}/finalize", response_model=TripRead)
def finalize_trip(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> Trip:
    """Computes distance/speed stats from the trip's GPS points and persists
    them on the trip. Call this after the app has synced its recorded points
    (see android Sync work) — with no points yet, stats just come back null.
    """
    trip = _get_owned_trip(db, trip_id, current_user.id)
    points = (
        db.query(GpsPoint)
        .filter(GpsPoint.trip_id == trip_id)
        .order_by(GpsPoint.recorded_at)
        .all()
    )
    stats = compute_trip_stats(points)
    trip.distance_km = stats.distance_km
    trip.max_speed = stats.max_speed
    trip.min_speed = stats.min_speed
    trip.avg_speed = stats.avg_speed
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


@router.get("/{trip_id}/segments", response_model=List[TripSegmentRead])
def get_trip_segments(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> list[TripSegmentRead]:
    """Slow/fast segments computed on the fly from the trip's GPS points,
    relative to the trip's own average speed — no dedicated table.
    """
    _get_owned_trip(db, trip_id, current_user.id)
    points = (
        db.query(GpsPoint)
        .filter(GpsPoint.trip_id == trip_id)
        .order_by(GpsPoint.recorded_at)
        .all()
    )
    segments = compute_trip_segments(points)
    return [
        TripSegmentRead(
            segment_type=s.segment_type,
            start_lat=s.start_lat,
            start_lng=s.start_lng,
            end_lat=s.end_lat,
            end_lng=s.end_lng,
            start_time=s.start_time,
            end_time=s.end_time,
            avg_speed=s.avg_speed,
        )
        for s in segments
    ]


# --- Stops (nested under a trip) ---


@router.post("/{trip_id}/stops", response_model=StopRead, status_code=status.HTTP_201_CREATED)
def create_stop(
    trip_id: str,
    stop_in: StopCreate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Stop:
    _get_owned_trip(db, trip_id, current_user.id)
    stop = Stop(trip_id=trip_id, **stop_in.model_dump())
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop


@router.get("/{trip_id}/stops", response_model=List[StopRead])
def list_stops(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> list[Stop]:
    _get_owned_trip(db, trip_id, current_user.id)
    return db.query(Stop).filter(Stop.trip_id == trip_id).order_by(Stop.sequence).all()


@router.patch("/{trip_id}/stops/{stop_id}", response_model=StopRead)
def update_stop(
    trip_id: str,
    stop_id: str,
    stop_in: StopUpdate,
    db: DbDep,
    current_user: CurrentUserDep,
) -> Stop:
    _get_owned_trip(db, trip_id, current_user.id)
    stop = db.query(Stop).filter(Stop.id == stop_id, Stop.trip_id == trip_id).first()
    if stop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")
    for field, value in stop_in.model_dump(exclude_unset=True).items():
        setattr(stop, field, value)
    db.add(stop)
    db.commit()
    db.refresh(stop)
    return stop


@router.delete("/{trip_id}/stops/{stop_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_stop(trip_id: str, stop_id: str, db: DbDep, current_user: CurrentUserDep) -> None:
    _get_owned_trip(db, trip_id, current_user.id)
    stop = db.query(Stop).filter(Stop.id == stop_id, Stop.trip_id == trip_id).first()
    if stop is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Stop not found")
    db.delete(stop)
    db.commit()


# --- GPS points (nested under a trip) ---


@router.post(
    "/{trip_id}/gps-points",
    response_model=List[GpsPointRead],
    status_code=status.HTTP_201_CREATED,
)
def create_gps_points(
    trip_id: str,
    points_in: List[GpsPointCreate],
    db: DbDep,
    current_user: CurrentUserDep,
) -> list[GpsPoint]:
    # Accepts a batch, since the app records many points per trip and
    # should upload them periodically rather than one request per point.
    _get_owned_trip(db, trip_id, current_user.id)
    points = [GpsPoint(trip_id=trip_id, **p.model_dump()) for p in points_in]
    db.add_all(points)
    db.commit()
    for point in points:
        db.refresh(point)
    return points


@router.get("/{trip_id}/gps-points", response_model=List[GpsPointRead])
def list_gps_points(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> list[GpsPoint]:
    _get_owned_trip(db, trip_id, current_user.id)
    return (
        db.query(GpsPoint)
        .filter(GpsPoint.trip_id == trip_id)
        .order_by(GpsPoint.recorded_at)
        .all()
    )
