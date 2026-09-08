from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .routers import auth


settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.DATABASE_URL:
        raise RuntimeError(
            "DATABASE_URL is not set. Create a .env file with "
            "DATABASE_URL=postgresql+psycopg2://user:pass@host:5432/dbname"
        )
    if not settings.SECRET_KEY:
        raise RuntimeError("SECRET_KEY is not set. Create a .env file with a secure secret key.")
    yield


app = FastAPI(title="TripTrace API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


app.include_router(auth.router)

# TODO: include trips, stops, and gps_points routers once implemented
