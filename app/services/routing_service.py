import math
from datetime import datetime
from typing import List, Optional, Sequence, Tuple

import httpx

from ..config import get_settings

ROUTES_API_URL = "https://routes.googleapis.com/directions/v2:computeRoutes"


class RouteStep:
    def __init__(self, maneuver: str, instructions: str, distance_meters: int, encoded_polyline: str):
        self.maneuver = maneuver
        self.instructions = instructions
        self.distance_meters = distance_meters
        self.encoded_polyline = encoded_polyline


class RouteResult:
    def __init__(
        self,
        duration_seconds: int,
        distance_meters: int,
        encoded_polyline: str,
        steps: Optional[List[RouteStep]] = None,
        description: str = "",
    ):
        self.duration_seconds = duration_seconds
        self.distance_meters = distance_meters
        self.encoded_polyline = encoded_polyline
        # Empty unless include_steps=True was passed — calculate_trip_route
        # (the one-time call before a trip starts) has no use for turn-by-turn
        # data, only recalculate_trip_eta's live navigation view does.
        self.steps = steps or []
        self.description = description


class RoutingError(Exception):
    """Raised when the Routes API call fails or returns no usable route."""


def compute_route(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    departure_time: Optional[datetime] = None,
    include_steps: bool = False,
    via_points: Sequence[Tuple[float, float]] = (),
) -> RouteResult:
    """Google's preferred route (the first one it returns)."""
    return compute_routes(
        origin_lat,
        origin_lng,
        destination_lat,
        destination_lng,
        departure_time=departure_time,
        include_steps=include_steps,
        via_points=via_points,
    )[0]


def compute_routes(
    origin_lat: float,
    origin_lng: float,
    destination_lat: float,
    destination_lng: float,
    departure_time: Optional[datetime] = None,
    include_steps: bool = False,
    via_points: Sequence[Tuple[float, float]] = (),
    alternatives: bool = False,
) -> List[RouteResult]:
    """Every route Google returns, preferred one first. With
    alternatives=True Google may add up to 3 more, or none; it rejects
    alternatives combined with intermediates, so via_points wins and
    alternatives is ignored when both are given.
    """
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
        # Without this, Google defaults navigationInstruction.instructions to
        # English — harmless while only the polyline/duration were used, but
        # would have shipped "Turn right onto Main Street" into an
        # all-Spanish, voseo app the moment per-step instructions started
        # being requested. es-419 = Latin American Spanish; matches the
        # app's own voseo (vos, not tú) better than plain "es" (which leans
        # Spain-Spanish conventions).
        "languageCode": "es-419",
    }
    if departure_time is not None:
        body["departureTime"] = departure_time.isoformat()
    if via_points:
        # "via": True makes each one a pass-through point: the route goes
        # through it without stopping there, and Google keeps returning a
        # single leg instead of splitting the route at every point.
        # The heading (from the point before to the point after) makes Google
        # snap each point to the lane going our way. Without it, a point on a
        # divided road can land on the opposite lane and force a U-turn loop.
        path = [(origin_lat, origin_lng), *via_points, (destination_lat, destination_lng)]
        body["intermediates"] = [
            {
                "location": {
                    "latLng": {"latitude": lat, "longitude": lng},
                    "heading": _bearing_degrees(path[i], path[i + 2]),
                },
                "via": True,
            }
            for i, (lat, lng) in enumerate(via_points)
        ]
    elif alternatives:
        body["computeAlternativeRoutes"] = True

    field_mask = "routes.duration,routes.distanceMeters,routes.polyline.encodedPolyline"
    if body.get("computeAlternativeRoutes"):
        field_mask += ",routes.description"
    if include_steps:
        # Per-step turn-by-turn data for the live in-app navigation view —
        # same Pro-tier billing as the fields above, Google only ever sends
        # what's explicitly asked for here, regardless of what the caller
        # does with the response afterwards. Each step's own polyline is
        # requested too (unused for now) since it's the same field-mask
        # cost either way and useful later, e.g. to highlight just the
        # current step's stretch of road.
        field_mask += (
            ",routes.legs.steps.navigationInstruction"
            ",routes.legs.steps.distanceMeters"
            ",routes.legs.steps.polyline.encodedPolyline"
        )

    headers = {
        "Content-Type": "application/json",
        "X-Goog-Api-Key": settings.GOOGLE_ROUTES_API_KEY,
        # Required by the API — there's no default field list, omitting
        # this causes an error, not just a bigger response.
        "X-Goog-FieldMask": field_mask,
    }

    try:
        response = httpx.post(ROUTES_API_URL, json=body, headers=headers, timeout=10.0)
        response.raise_for_status()
    except httpx.HTTPStatusError as e:
        # e itself (str(e), from raise_for_status()) is just "Client error
        # '400 Bad Request' for url '...'" — the actually useful part is
        # Google's own JSON error body (reason, message), which raise_for_status
        # doesn't include. Reading it here is what makes future failures
        # self-diagnosing instead of a generic wrapper with no real detail.
        raise RoutingError(
            f"Routes API returned {e.response.status_code}: {e.response.text}"
        ) from e
    except httpx.HTTPError as e:
        # Connection-level failures (timeout, DNS, etc.) have no response
        # body to read — str(e) is all there is here.
        raise RoutingError(f"Routes API request failed: {e}") from e

    data = response.json()
    routes = data.get("routes")
    if not routes:
        raise RoutingError("Routes API returned no routes")

    return [_parse_route(route, include_steps) for route in routes]


def _bearing_degrees(start: Tuple[float, float], end: Tuple[float, float]) -> int:
    """Initial compass bearing from start to end, 0-359 (0 = north)."""
    lat1, lng1 = map(math.radians, start)
    lat2, lng2 = map(math.radians, end)
    d_lng = lng2 - lng1
    x = math.sin(d_lng) * math.cos(lat2)
    y = math.cos(lat1) * math.sin(lat2) - math.sin(lat1) * math.cos(lat2) * math.cos(d_lng)
    return round(math.degrees(math.atan2(x, y))) % 360


def _parse_route(route: dict, include_steps: bool) -> RouteResult:
    try:
        # duration comes back as a string like "1234s" (seconds, Duration proto)
        duration_seconds = int(route["duration"].rstrip("s"))
        distance_meters = route["distanceMeters"]
        encoded_polyline = route["polyline"]["encodedPolyline"]
    except (KeyError, ValueError) as e:
        raise RoutingError(f"Unexpected Routes API response shape: {e}") from e

    steps: List[RouteStep] = []
    if include_steps:
        # Always a single leg: the only intermediates ever sent are via
        # points, which don't split the route (stops are tracked separately,
        # via proximity detection against recorded GPS points, not as
        # routing waypoints). Looping over legs anyway keeps this correct if
        # that ever changes.
        for leg in route.get("legs", []):
            for step in leg.get("steps", []):
                nav = step.get("navigationInstruction", {})
                steps.append(
                    RouteStep(
                        maneuver=nav.get("maneuver", "STRAIGHT"),
                        instructions=nav.get("instructions", ""),
                        distance_meters=step.get("distanceMeters", 0),
                        encoded_polyline=step.get("polyline", {}).get("encodedPolyline", ""),
                    )
                )

    return RouteResult(
        duration_seconds=duration_seconds,
        distance_meters=distance_meters,
        encoded_polyline=encoded_polyline,
        steps=steps,
        description=route.get("description", ""),
    )
