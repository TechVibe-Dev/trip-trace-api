import re

from fastapi import Request
from fastapi.responses import JSONResponse
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded


# Render's standard start command for this app (uvicorn main:app --host
# 0.0.0.0 --port $PORT) doesn't tell uvicorn to trust X-Forwarded-For, so
# request.client.host — what slowapi's own get_remote_address key_func
# reads — would be Render's internal proxy address for every request, not
# the real caller. That would make the rate limit apply to all callers
# combined instead of per-IP, which defeats the point. Reading the header
# ourselves works regardless of uvicorn's startup flags, since Render sets
# it before the request reaches the app either way.
def get_client_ip(request: Request) -> str:
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        # A chain of comma-separated hops (client, proxy1, proxy2, ...) —
        # the first entry is the original client.
        return forwarded_for.split(",")[0].strip()
    # Local/dev fallback, where there's no proxy in front at all.
    return request.client.host if request.client else "unknown"


limiter = Limiter(key_func=get_client_ip)

_UNIT_SECONDS = {"second": 1, "minute": 60, "hour": 3600, "day": 86400}
_DEFAULT_RETRY_AFTER_SECONDS = 60


# Custom, instead of slowapi's own _rate_limit_exceeded_handler — that one
# returns a bare {"error": "Rate limit exceeded: 3 per 1 minute"}, with
# nothing a client can use directly to show "try again in N seconds"
# without parsing English prose itself. exc.detail already contains that
# same "3 per 1 minute" text (built by slowapi from whatever limit string
# the endpoint declared, e.g. "3/minute") — parsed here into a plain
# retry_after_seconds field, so this handler stays correct automatically if
# a limit's window ever changes at the decorator, without needing an edit
# here too.
def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded) -> JSONResponse:
    retry_after_seconds = _DEFAULT_RETRY_AFTER_SECONDS
    match = re.search(r"per (\d+) (\w+)", exc.detail)
    if match:
        amount, unit = match.groups()
        unit_seconds = _UNIT_SECONDS.get(unit.rstrip("s"), _DEFAULT_RETRY_AFTER_SECONDS)
        retry_after_seconds = int(amount) * unit_seconds

    return JSONResponse(
        status_code=429,
        content={
            "detail": "Too many requests. Please try again later.",
            "retry_after_seconds": retry_after_seconds,
        },
        # Retry-After is the standard HTTP header for this — set alongside
        # the JSON field so either generic HTTP tooling or the app's own
        # client code can use whichever is more convenient.
        headers={"Retry-After": str(retry_after_seconds)},
    )
