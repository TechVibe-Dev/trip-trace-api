from datetime import timedelta
from typing import Annotated, List

from fastapi import APIRouter, Depends, HTTPException, Request, status

from ..dependencies import get_current_user
from ..models.user import User
from ..rate_limit import limiter
from ..schemas.saved_route import RoutePreview, RoutePreviewRequest
from ..services.routing_service import RoutingError, compute_routes
from .trips import _future_departure_time

router = APIRouter(prefix="/api/v1/routes", tags=["routes"])

CurrentUserDep = Annotated[User, Depends(get_current_user)]


# Rate-limited because, unlike calculate-route, nothing ties a preview to a
# saved trip: each call is a billed Google request. 20 a minute is plenty
# for someone moving via points around on the map.
@router.post("/preview", response_model=List[RoutePreview])
@limiter.limit("20/minute")
def preview_routes(
    request: Request,
    preview_in: RoutePreviewRequest,
    current_user: CurrentUserDep,
) -> List[RoutePreview]:
    """Routes for an origin and destination before any trip exists, so the
    Create trip screen can draw them on the map and let the user pick or
    adjust one. Nothing is persisted.

    Returns Google's preferred route first. With via_points, that is the
    only one: it follows the points. Without them and with
    alternatives=true, up to 3 more may follow.
    """
    departure_time = _future_departure_time(preview_in.planned_departure_at)

    try:
        routes = compute_routes(
            origin_lat=preview_in.origin_lat,
            origin_lng=preview_in.origin_lng,
            destination_lat=preview_in.destination_lat,
            destination_lng=preview_in.destination_lng,
            departure_time=departure_time,
            via_points=[(p.lat, p.lng) for p in preview_in.via_points],
            alternatives=preview_in.alternatives,
        )
    except RoutingError as e:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Could not preview route: {e}",
        ) from e

    return [
        RoutePreview(
            duration_seconds=r.duration_seconds,
            distance_meters=r.distance_meters,
            calculated_arrival_at=departure_time + timedelta(seconds=r.duration_seconds),
            route_polyline=r.encoded_polyline,
            description=r.description,
        )
        for r in routes
    ]
