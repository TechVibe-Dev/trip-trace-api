from datetime import datetime

from pydantic import BaseModel, Field

LATITUDE = Field(ge=-90, le=90)
LONGITUDE = Field(ge=-180, le=180)


class FavoritePlaceCreate(BaseModel):
    name: str
    lat: float = LATITUDE
    lng: float = LONGITUDE


class FavoritePlaceRead(BaseModel):
    id: str
    user_id: str
    name: str
    lat: float
    lng: float
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
