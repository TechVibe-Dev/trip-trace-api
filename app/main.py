from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from .config import get_settings
from .rate_limit import limiter
from .routers import auth, favorite_places, trips


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

# Wired in for the rate limits declared on individual endpoints (see
# routers/auth.py) — a 429 with a clean JSON body instead of an unhandled
# exception when a limit is hit.
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

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
app.include_router(trips.router)
app.include_router(favorite_places.router)
