from datetime import datetime

from ..models.gps_point import GpsPoint
from ..models.stop import Stop
from .trip_stats_service import haversine_distance_km

# How close a recorded GPS point needs to be to a stop's coordinates to
# count as "reached" — roughly one city block. Tight enough to not confuse
# a stop with one on a nearby street, loose enough to tolerate normal GPS
# drift (which can easily be 10-20m, more around tall buildings).
STOP_PROXIMITY_METERS = 100.0


def find_newly_reached_stops(
    points: list[GpsPoint],
    unreached_stops: list[Stop],
) -> dict[str, datetime]:
    """Checks a batch of newly-uploaded GPS points against a trip's stops
    that haven't been reached yet (actual_arrival_at is None).

    Returns {stop_id: recorded_at} for every stop now within
    STOP_PROXIMITY_METERS of at least one of the points — using the
    earliest matching point's recorded_at as the arrival time. Callers are
    responsible for persisting this onto each Stop.

    `points` should be sorted by recorded_at ascending (the order they come
    back from create_gps_points, matching the order they were submitted)
    so "earliest matching point" is well-defined.
    """
    reached: dict[str, datetime] = {}
    for stop in unreached_stops:
        for point in points:
            distance_km = haversine_distance_km(stop.lat, stop.lng, point.lat, point.lng)
            if distance_km * 1000 <= STOP_PROXIMITY_METERS:
                reached[stop.id] = point.recorded_at
                break
    return reached
