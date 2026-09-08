import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, String, Text, func
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

    status: Mapped[TripStatus] = mapped_column(
        SqlEnum(TripStatus, name="trip_status"),
        nullable=False,
        default=TripStatus.PLANNED,
    )

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
