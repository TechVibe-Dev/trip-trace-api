from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from ..models.stop import StopType
from ..models.trip import TripStatus

# Valid ranges for real-world coordinates — latitude spans the poles,
# longitude wraps the globe. Rejecting out-of-range values here (422) is
# cheap insurance now that three separate clients (Android app, web
# frontend, Telegram bot) all send coordinates to this API.
LATITUDE = Field(ge=-90, le=90)
LONGITUDE = Field(ge=-180, le=180)


class TripCreate(BaseModel):
    origin_name: str
    origin_lat: float = LATITUDE
    origin_lng: float = LONGITUDE
    destination_name: str
    destination_lat: float = LATITUDE
    destination_lng: float = LONGITUDE
    planned_route_polyline: Optional[str] = None
    planned_departure_at: Optional[datetime] = None
    desired_arrival_at: Optional[datetime] = None
    calculated_arrival_at: Optional[datetime] = None


class TripUpdate(BaseModel):
    status: Optional[TripStatus] = None
    planned_departure_at: Optional[datetime] = None
    desired_arrival_at: Optional[datetime] = None
    calculated_arrival_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    ended_at: Optional[datetime] = None
    distance_km: Optional[float] = None
    max_speed: Optional[float] = None
    min_speed: Optional[float] = None
    avg_speed: Optional[float] = None


class TripRead(BaseModel):
    id: str
    user_id: str
    origin_name: str
    origin_lat: float
    origin_lng: float
    destination_name: str
    destination_lat: float
    destination_lng: float
    planned_route_polyline: Optional[str]
    status: TripStatus
    planned_departure_at: Optional[datetime]
    desired_arrival_at: Optional[datetime]
    calculated_arrival_at: Optional[datetime]
    started_at: Optional[datetime]
    ended_at: Optional[datetime]
    distance_km: Optional[float]
    max_speed: Optional[float]
    min_speed: Optional[float]
    avg_speed: Optional[float]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class StopCreate(BaseModel):
    type: StopType
    name: Optional[str] = None
    lat: float = LATITUDE
    lng: float = LONGITUDE
    planned_arrival_at: Optional[datetime] = None
    sequence: int


class StopUpdate(BaseModel):
    actual_arrival_at: Optional[datetime] = None
    departure_at: Optional[datetime] = None


class StopRead(BaseModel):
    id: str
    trip_id: str
    type: StopType
    name: Optional[str]
    lat: float
    lng: float
    planned_arrival_at: Optional[datetime]
    actual_arrival_at: Optional[datetime]
    departure_at: Optional[datetime]
    sequence: int

    model_config = {"from_attributes": True}


class GpsPointCreate(BaseModel):
    lat: float = LATITUDE
    lng: float = LONGITUDE
    speed: Optional[float] = None
    accuracy: Optional[float] = None
    bearing: Optional[float] = None
    recorded_at: datetime


class GpsPointRead(BaseModel):
    id: int
    trip_id: str
    lat: float
    lng: float
    speed: Optional[float]
    accuracy: Optional[float]
    bearing: Optional[float]
    recorded_at: datetime

    model_config = {"from_attributes": True}


class TripSegmentRead(BaseModel):
    segment_type: str
    start_lat: float
    start_lng: float
    end_lat: float
    end_lng: float
    start_time: datetime
    end_time: datetime
    avg_speed: float


class EtaRecalculation(BaseModel):
    # Deliberately NOT persisted on the Trip (see recalculate_eta in
    # routers/trips.py) — calculated_arrival_at keeps meaning "the original
    # plan", this is a live snapshot computed from wherever the trip is
    # right now.
    calculated_arrival_at: datetime
    route_polyline: str
