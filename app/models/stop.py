import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy import Enum as SqlEnum
from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ..database import Base


class StopType(str, enum.Enum):
    PLANNED = "PLANNED"    # defined by the user before the trip
    DETECTED = "DETECTED"  # inferred from sustained near-zero speed


class Stop(Base):
    __tablename__ = "stops"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    trip_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("trips.id", ondelete="CASCADE"), nullable=False, index=True
    )

    type: Mapped[StopType] = mapped_column(
        SqlEnum(StopType, name="stop_type"), nullable=False
    )
    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    lat: Mapped[float] = mapped_column(Float, nullable=False)
    lng: Mapped[float] = mapped_column(Float, nullable=False)

    arrival_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    departure_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)

    trip: Mapped["Trip"] = relationship("Trip", back_populates="stops")
