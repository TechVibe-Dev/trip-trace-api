from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from .trip import LATITUDE, LONGITUDE, MAX_ROUTED_STOPS, MAX_VIA_POINTS, ViaPoint


class SavedRouteCreate(BaseModel):
    name: str
    origin_name: str
    origin_lat: float = LATITUDE
    origin_lng: float = LONGITUDE
    destination_name: str
    destination_lat: float = LATITUDE
    destination_lng: float = LONGITUDE
    # At least one: a saved route without via points is just "let Google
    # choose", which needs no saving.
    via_points: List[ViaPoint] = Field(min_length=1, max_length=MAX_VIA_POINTS)


class SavedRouteUpdate(BaseModel):
    name: Optional[str] = None
    via_points: Optional[List[ViaPoint]] = Field(default=None, min_length=1, max_length=MAX_VIA_POINTS)


class SavedRouteRead(BaseModel):
    id: str
    user_id: str
    name: str
    origin_name: str
    origin_lat: float
    origin_lng: float
    destination_name: str
    destination_lat: float
    destination_lng: float
    via_points: List[ViaPoint]
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RoutePreviewRequest(BaseModel):
    origin_lat: float = LATITUDE
    origin_lng: float = LONGITUDE
    destination_lat: float = LATITUDE
    destination_lng: float = LONGITUDE
    via_points: List[ViaPoint] = Field(default_factory=list, max_length=MAX_VIA_POINTS)
    # The trip's planned stops, in order. Merged into the via points the
    # same way calculate-route does, so the preview matches the real route.
    stops: List[ViaPoint] = Field(default_factory=list, max_length=MAX_ROUTED_STOPS)
    planned_departure_at: Optional[datetime] = None
    # Ask Google for up to 3 more routes besides its preferred one. Ignored
    # when via_points or stops is not empty: Google doesn't support both at
    # once.
    alternatives: bool = False


class RoutePreview(BaseModel):
    duration_seconds: int
    distance_meters: int
    calculated_arrival_at: datetime
    route_polyline: str
    # Only filled for alternatives.
    description: str
