import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import JSON, Float, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class TripStatus(str, enum.Enum):
    PLANNED = "PLANNED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )

    origin_name: Mapped[str] = mapped_column(String(255), nullable=False)
    origin_lat: Mapped[float] = mapped_column(Float, nullable=False)
    origin_lng: Mapped[float] = mapped_column(Float, nullable=False)

    destination_name: Mapped[str] = mapped_column(String(255), nullable=False)
    destination_lat: Mapped[float] = mapped_column(Float, nullable=False)
    destination_lng: Mapped[float] = mapped_column(Float, nullable=False)

    # Raw geometry from a Directions-style API, kept as an encoded polyline
    # rather than expanded into rows — it's a reference line, not telemetry.
    planned_route_polyline: Mapped[str | None] = mapped_column(Text, nullable=True)

    # User-chosen points the route must pass through, in order, as a list of
    # {"name", "lat", "lng"} dicts. Sent to Google as pass-through waypoints
    # so the suggested route follows the road the user picked (e.g. "by the
    # Rambla and Ruta 101") instead of whatever Google finds fastest. Not
    # stops: the car is not expected to halt at them. Null or empty = let
    # Google choose.
    via_points: Mapped[list | None] = mapped_column(JSON, nullable=True)
    # Name of the chosen route, copied from the saved route it came from (or
    # typed for a one-off), so it survives that saved route being renamed
    # or deleted. Kept after the user lets go of the route mid-trip: it
    # records what was planned.
    route_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    saved_route_id: Mapped[str | None] = mapped_column(
        String(36), ForeignKey("saved_routes.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[TripStatus] = mapped_column(
        SqlEnum(TripStatus, name="trip_status"),
        nullable=False,
        default=TripStatus.PLANNED,
    )

    # Set when the trip is created (Create trip screen).
    planned_departure_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    desired_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    # ETA computed at creation time (routing/traffic), shown as "Planeado"
    # during the active trip. Distinct from the live-recalculated ETA, which
    # isn't persisted.
    calculated_arrival_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Set when the trip actually happens.
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    # Denormalized metrics, computed once when the trip is closed so the
    # dashboard doesn't have to scan gps_points on every read.
    distance_km: Mapped[float | None] = mapped_column(Float, nullable=True)
    max_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    min_speed: Mapped[float | None] = mapped_column(Float, nullable=True)
    avg_speed: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["User"] = relationship("User", back_populates="trips")
    stops: Mapped[list["Stop"]] = relationship(
        "Stop",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="Stop.sequence",
    )
    gps_points: Mapped[list["GpsPoint"]] = relationship(
        "GpsPoint",
        back_populates="trip",
        cascade="all, delete-orphan",
        order_by="GpsPoint.recorded_at",
    )
