import math
from datetime import datetime, timedelta, timezone
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
    EtaRecalculation,
    GpsPointCreate,
    GpsPointRead,
    RouteStepRead,
    StopCreate,
    StopRead,
    StopUpdate,
    TripCreate,
    TripRead,
    TripSegmentRead,
    TripUpdate,
)
from ..services.routing_service import RoutingError, compute_route
from ..services.stop_detection_service import STOP_PROXIMITY_METERS, find_newly_reached_stops
from ..services.trip_stats_service import (
    compute_trip_segments,
    compute_trip_stats,
    haversine_distance_km,
)

router = APIRouter(prefix="/api/v1/trips", tags=["trips"])

DbDep = Annotated[Session, Depends(get_db)]
CurrentUserDep = Annotated[User, Depends(get_current_user)]

# Google rejects a departureTime that isn't STRICTLY in the future (confirmed
# via its own error: "Timestamp must be set to a future time.", INVALID_ARGUMENT)
# — a bare now() is usually already in the past by the time it reaches
# Google's servers (network round-trip, serialization), even though it was
# accurate the instant we read it. This buffer absorbs that gap.
DEPARTURE_TIME_BUFFER = timedelta(minutes=1)

# Past this much time since a trip started, recalculate-eta stops calling
# Google Routes and returns an empty route instead. Guards against a "ghost"
# trip that never gets finalized (dead battery, app killed, user forgets):
# the app polls every ~30s, which alone would burn through the Routes free
# tier in under two days. Generous enough for any real trip; the app keeps
# recording and showing live position, it just stops getting a route.
MAX_LIVE_ROUTING_DURATION = timedelta(hours=10)


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


def _future_departure_time(planned_departure_at: Optional[datetime]) -> datetime:
    now = datetime.now(timezone.utc)
    if planned_departure_at and planned_departure_at > now:
        return planned_departure_at
    return now + DEPARTURE_TIME_BUFFER


@router.post("/{trip_id}/calculate-route", response_model=TripRead)
def calculate_trip_route(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> Trip:
    """Calls Google Routes (traffic-aware) using the trip's own
    origin/destination/planned_departure_at, and persists the resulting ETA
    and route polyline on the trip.

    Uses the current time (plus a small buffer, see DEPARTURE_TIME_BUFFER)
    instead of planned_departure_at whenever that's unset OR already in the
    past (an "ahora" trip, or a planned trip whose departure time has since
    passed) — TRAFFIC_AWARE routing needs a future departure time; Google's
    Routes API returns 400 otherwise, since it can't compute live traffic
    for a moment that already happened.
    """
    trip = _get_owned_trip(db, trip_id, current_user.id)
    departure_time = _future_departure_time(trip.planned_departure_at)

    try:
        route = compute_route(
            origin_lat=trip.origin_lat,
            origin_lng=trip.origin_lng,
            destination_lat=trip.destination_lat,
            destination_lng=trip.destination_lng,
            departure_time=departure_time,
        )
    except RoutingError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not calculate route: {e}",
        ) from e

    trip.calculated_arrival_at = departure_time + timedelta(seconds=route.duration_seconds)
    trip.planned_route_polyline = route.encoded_polyline
    db.add(trip)
    db.commit()
    db.refresh(trip)
    return trip


def _live_routing_expired(db: Session, trip: Trip) -> bool:
    started_at = trip.started_at
    if started_at is None:
        # Clients are expected to set started_at, but don't let a trip that
        # lacks it bypass the cap: fall back to its first recorded point.
        started_at = (
            db.query(GpsPoint.recorded_at)
            .filter(GpsPoint.trip_id == trip.id)
            .order_by(GpsPoint.recorded_at.asc())
            .limit(1)
            .scalar()
        )
    if started_at is None:
        return False
    if started_at.tzinfo is None:
        started_at = started_at.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) - started_at > MAX_LIVE_ROUTING_DURATION


def _has_reached_destination(db: Session, trip: Trip) -> bool:
    """True once any recorded point of the trip has come within
    STOP_PROXIMITY_METERS of its destination (the same radius the app uses
    for its "you've arrived" prompt). Sticky on purpose: after arriving, a
    route back to the same destination is useless, even if the user chose
    to keep the trip going and drove off.
    """
    # Cheap SQL bounding-box prefilter, then an exact haversine check on the
    # few candidates, instead of scanning every point of the trip in Python.
    lat_margin = STOP_PROXIMITY_METERS / 111_000
    lng_margin = lat_margin / max(math.cos(math.radians(trip.destination_lat)), 0.01)
    candidates = (
        db.query(GpsPoint.lat, GpsPoint.lng)
        .filter(
            GpsPoint.trip_id == trip.id,
            GpsPoint.lat.between(trip.destination_lat - lat_margin, trip.destination_lat + lat_margin),
            GpsPoint.lng.between(trip.destination_lng - lng_margin, trip.destination_lng + lng_margin),
        )
        .all()
    )
    return any(
        haversine_distance_km(lat, lng, trip.destination_lat, trip.destination_lng) * 1000
        <= STOP_PROXIMITY_METERS
        for lat, lng in candidates
    )


@router.post("/{trip_id}/recalculate-eta", response_model=EtaRecalculation)
def recalculate_trip_eta(trip_id: str, db: DbDep, current_user: CurrentUserDep) -> EtaRecalculation:
    """Live ETA for a trip already in progress: same Google Routes call as
    calculate-route, but using the most recently recorded GPS point as the
    origin instead of the trip's original starting point.

    Deliberately does NOT persist onto the trip — calculated_arrival_at
    keeps meaning "the original plan"; this is a snapshot of "given where
    the trip actually is right now". Callers (the Android app, polling
    every ~30s while a trip is active) hold onto this client-side instead.

    Also requests turn-by-turn steps, for the live in-app navigation view —
    since this route is computed FROM the trip's current position, steps[0]
    is always "the next maneuver from here": no separate step-matching is
    needed on the client, the freshest poll already carries it.
    """
    trip = _get_owned_trip(db, trip_id, current_user.id)

    latest_point = (
        db.query(GpsPoint)
        .filter(GpsPoint.trip_id == trip_id)
        .order_by(GpsPoint.recorded_at.desc())
        .first()
    )
    if latest_point is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No GPS points recorded yet for this trip",
        )

    if _live_routing_expired(db, trip) or _has_reached_destination(db, trip):
        # Same shape the app already handles before its first poll returns:
        # no suggested route line, no turn card, and the arrival time falls
        # back to the trip's original plan.
        return EtaRecalculation(calculated_arrival_at=None, route_polyline="", steps=[])

    departure_time = _future_departure_time(None)

    try:
        route = compute_route(
            origin_lat=latest_point.lat,
            origin_lng=latest_point.lng,
            destination_lat=trip.destination_lat,
            destination_lng=trip.destination_lng,
            departure_time=departure_time,
            include_steps=True,
        )
    except RoutingError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not recalculate ETA: {e}",
        ) from e

    return EtaRecalculation(
        calculated_arrival_at=departure_time + timedelta(seconds=route.duration_seconds),
        route_polyline=route.encoded_polyline,
        steps=[
            RouteStepRead(
                maneuver=s.maneuver,
                instructions=s.instructions,
                distance_meters=s.distance_meters,
                polyline=s.encoded_polyline,
            )
            for s in route.steps
        ],
    )


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

    # Side effect: check whether any of the points just uploaded brought the
    # trip within range of a stop that hasn't been reached yet (live stop
    # progress). Points are already in submission order (== recorded_at
    # ascending, same as the request body), matching what
    # find_newly_reached_stops expects.
    unreached_stops = (
        db.query(Stop)
        .filter(Stop.trip_id == trip_id, Stop.actual_arrival_at.is_(None))
        .all()
    )
    if unreached_stops:
        reached = find_newly_reached_stops(points, unreached_stops)
        for stop in unreached_stops:
            if stop.id in reached:
                stop.actual_arrival_at = reached[stop.id]
                db.add(stop)
        if reached:
            db.commit()

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
