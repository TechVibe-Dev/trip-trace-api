from fastapi import Request
from slowapi import Limiter


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
