from typing import Callable
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.types import ASGIApp

from app.core.config import settings
from app.core.rate_limiter import RedisRateLimiter
from app.core.network_utils import get_client_ip

from functools import wraps
from fastapi import HTTPException

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Global rate limiter by IP using Redis token bucket.
    Default limits from settings (can be overridden per-route via decorator).
    """
    def __init__(self, app: ASGIApp, limiter: RedisRateLimiter):
        super().__init__(app)
        self.limiter = limiter
        # defaults
        self.capacity = settings.RATE_LIMIT_CAPACITY  # e.g. 300
        self.refill_per_sec = settings.RATE_LIMIT_REFILL_PER_SEC  # e.g. 5 -> 300/60 = 5/sec

    async def dispatch(self, request: Request, call_next: Callable):
        ip = get_client_ip(request) or "unknown"
        key = f"rl:ip:{ip}"
        allowed, remaining = await self.limiter.allow_request(
            key, capacity=self.capacity, refill_per_sec=self.refill_per_sec, requested=1
        )
        # set headers for observability
        headers = {
            "X-RateLimit-Limit": str(self.capacity),
            "X-RateLimit-Remaining": str(remaining),
        }
        if not allowed:
            # specify Retry-After in seconds (approx)
            retry_after = max(1, int(self.capacity / max(1, self.refill_per_sec)))
            headers["Retry-After"] = str(retry_after)
            return JSONResponse(status_code=429, content={"detail": "Too Many Requests"}, headers=headers)
        # pass to app, but ensure headers preserved
        response = await call_next(request)
        for k,v in headers.items():
            response.headers.setdefault(k, v)
        return response

def rate_limit(limit: int, window_seconds: int):
    """
    Decorator to apply per-route rate limit (tokens capacity=limit, refill_per_sec=limit/window).
    Usage:
      @router.post("/login")
      @rate_limit(limit=10, window_seconds=60)
      async def login(...):
          ...
    """
    refill = limit / max(1, window_seconds)
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # FastAPI passes request via dependency injection; we need Request object from args or kwargs
            request = None
            for a in args:
                if isinstance(a, Request):
                    request = a
                    break
            if not request:
                request = kwargs.get("request")
            ip = "unknown"
            if request:
                from app.core.network_utils import get_client_ip
                ip = get_client_ip(request) or "unknown"

            limiter: RedisRateLimiter = request.app.state.rate_limiter
            key = f"rl:route:{request.url.path}:ip:{ip}"
            allowed, remaining = await limiter.allow_request(key, capacity=limit, refill_per_sec=refill, requested=1)
            headers = {
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": str(remaining),
            }
            if not allowed:
                retry_after = max(1, int(limit / max(1, refill)))
                raise HTTPException(status_code=429, detail="Too Many Requests", headers={**headers, "Retry-After": str(retry_after)})
            # call original
            response = await func(*args, **kwargs)
            # ensure headers if Response-like
            try:
                response.headers["X-RateLimit-Limit"] = str(limit)
                response.headers["X-RateLimit-Remaining"] = str(remaining)
            except Exception:
                pass
            return response
        return wrapper
    return decorator
