from datetime import datetime
from typing import Optional

from pydantic import BaseModel

from ..models.stop import StopType
from ..models.trip import TripStatus


class TripCreate(BaseModel):
    origin_name: str
    origin_lat: float
    origin_lng: float
    destination_name: str
    destination_lat: float
    destination_lng: float
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
    lat: float
    lng: float
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
    lat: float
    lng: float
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
