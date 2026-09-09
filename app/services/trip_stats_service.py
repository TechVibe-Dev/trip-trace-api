import math
from datetime import datetime
from typing import Optional

from ..models.gps_point import GpsPoint


def _haversine_distance_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometers."""
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    d_phi = math.radians(lat2 - lat1)
    d_lambda = math.radians(lng2 - lng1)

    a = (
        math.sin(d_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(d_lambda / 2) ** 2
    )
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return earth_radius_km * c


class TripStats:
    def __init__(
        self,
        distance_km: Optional[float],
        max_speed: Optional[float],
        min_speed: Optional[float],
        avg_speed: Optional[float],
    ):
        self.distance_km = distance_km
        self.max_speed = max_speed
        self.min_speed = min_speed
        self.avg_speed = avg_speed


def compute_trip_stats(points: list[GpsPoint]) -> TripStats:
    """Computes distance and speed stats from a trip's ordered GPS points.

    Expects `points` already sorted by `recorded_at` ascending.
    """
    if not points:
        return TripStats(distance_km=None, max_speed=None, min_speed=None, avg_speed=None)

    speeds = [p.speed for p in points if p.speed is not None]
    max_speed = max(speeds) if speeds else None
    min_speed = min(speeds) if speeds else None

    total_distance_km = 0.0
    for previous, current in zip(points, points[1:]):
        total_distance_km += _haversine_distance_km(
            previous.lat, previous.lng, current.lat, current.lng
        )

    avg_speed: Optional[float] = None
    if len(points) >= 2:
        duration_hours = (
            points[-1].recorded_at - points[0].recorded_at
        ).total_seconds() / 3600
        # avg_speed = total distance / total time, not a plain average of the
        # instantaneous speed readings — this weights by how long each leg
        # actually took, not by how many points happened to be recorded.
        if duration_hours > 0:
            avg_speed = total_distance_km / duration_hours

    return TripStats(
        distance_km=round(total_distance_km, 2),
        max_speed=max_speed,
        min_speed=min_speed,
        avg_speed=round(avg_speed, 2) if avg_speed is not None else None,
    )


# Ratios relative to the trip's own average speed — a point is "slow" if
# it's well below the trip's pace (traffic, red lights) and "fast" if well
# above it. Deliberately simple: no comparison against historical data on
# the same road, no external traffic API — just the trip's own numbers.
SLOW_THRESHOLD_RATIO = 0.6
FAST_THRESHOLD_RATIO = 1.4


class TripSegment:
    def __init__(
        self,
        segment_type: str,
        start_lat: float,
        start_lng: float,
        end_lat: float,
        end_lng: float,
        start_time: datetime,
        end_time: datetime,
        avg_speed: float,
    ):
        self.segment_type = segment_type
        self.start_lat = start_lat
        self.start_lng = start_lng
        self.end_lat = end_lat
        self.end_lng = end_lng
        self.start_time = start_time
        self.end_time = end_time
        self.avg_speed = avg_speed


def compute_trip_segments(points: list[GpsPoint]) -> list[TripSegment]:
    """Groups a trip's GPS points into consecutive SLOW/NORMAL/FAST segments,
    relative to the trip's own average speed. Points without a speed reading
    are skipped entirely (can't classify them).
    """
    points_with_speed = [p for p in points if p.speed is not None]
    if len(points_with_speed) < 2:
        return []

    avg_speed = sum(p.speed for p in points_with_speed) / len(points_with_speed)
    if avg_speed == 0:
        return []

    def classify(speed: float) -> str:
        if speed < avg_speed * SLOW_THRESHOLD_RATIO:
            return "SLOW"
        if speed > avg_speed * FAST_THRESHOLD_RATIO:
            return "FAST"
        return "NORMAL"

    segments: list[TripSegment] = []
    current_type = classify(points_with_speed[0].speed)
    segment_points = [points_with_speed[0]]

    for point in points_with_speed[1:]:
        point_type = classify(point.speed)
        if point_type == current_type:
            segment_points.append(point)
        else:
            segments.append(_build_segment(current_type, segment_points))
            current_type = point_type
            segment_points = [point]

    segments.append(_build_segment(current_type, segment_points))
    return segments


def _build_segment(segment_type: str, points: list[GpsPoint]) -> TripSegment:
    speeds = [p.speed for p in points]
    return TripSegment(
        segment_type=segment_type,
        start_lat=points[0].lat,
        start_lng=points[0].lng,
        end_lat=points[-1].lat,
        end_lng=points[-1].lng,
        start_time=points[0].recorded_at,
        end_time=points[-1].recorded_at,
        avg_speed=sum(speeds) / len(speeds),
    )
