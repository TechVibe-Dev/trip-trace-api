from datetime import datetime
from typing import Optional

import httpx

from ..config import get_settings

ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


class RouteResult:
    def __init__(self, duration_seconds: int, distance_meters: int, encoded_polyline: str):
        self.duration_seconds = duration_seconds
        self.distance_meters = distance_meters
        self.encoded_polyline = encoded_polyline


class RoutingError(Exception):
    """Raised when the Routes API call fails or returns no usable route."""


def compute_route(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    departure_time: Optional[datetime] = None,
) -> RouteResult:
    settings = get_settings()
    if not settings.GOOGLE_ROUTES_API_KEY:
        raise RoutingError("GOOGLE_ROUTES_API_KEY is not set")

    body = {
        "origin": {"location": {"latLng": {"latitude": origin_lat, "longitude": origin_lng}}},
        "destination": {
            "location": {"latLng": {"latitude": destination_lat, "longitude": destination_lng}}
        },
        "travelMode": "DRIVE",
        # Uses live/predicted traffic conditions — this is the whole point of
        # picking Google Routes over a free option like OSRM (see PR discussion).
        "routingPreference": "TRAFFIC_AWARE",
    }
    if departure_time is not None:
        body["departureTime"] = departure_time.isoformat()

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_ROUTES_API_KEY,
        # Required by the API — there's no default field list, omitting
        # this causes an error, not just a bigger response.
        "X-Goog-FieldMask": "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline",
    }

    try:
        response = httpx.post(ROUTES_API_URL, json=body, headers=headers, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPError as e:
        raise RoutingError(f"Routes API request failed: {e}") from e

    data = response.json()
    routes = data.get("routes")
    if not routes:
        raise RoutingError("Routes API returned no routes")

    route = routes[0]
    try:
        # duration comes back as a string like "1234s" (seconds, Duration proto)
        duration_seconds = int(route["duration"].rstrip("s"))
        distance_meters = route["distanceMeters"]
        encoded_polyline = route["polyline"]["encodedPolyline"]
    except (KeyError, ValueError) as e:
        raise RoutingError(f"Unexpected Routes API response shape: {e}") from e

    return RouteResult(
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        encoded_polyline=encoded_polyline,
    )
