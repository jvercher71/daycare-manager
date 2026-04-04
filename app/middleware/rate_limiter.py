import time
import logging
import os
from collections import defaultdict
from fastapi import Request, HTTPException, status
from fastapi.responses import JSONResponse
from app.config import settings

logger = logging.getLogger("daycare_manager")

DISABLE_RATE_LIMIT = os.getenv("DISABLE_RATE_LIMIT", "false").lower() == "true"


class RateLimiter:
    def __init__(self, max_requests: int = None, window_seconds: int = None):
        self.max_requests = max_requests or settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, identifier: str) -> bool:
        if DISABLE_RATE_LIMIT:
            return True
        now = time.time()
        self.requests[identifier] = [
            ts for ts in self.requests[identifier]
            if now - ts < self.window_seconds
        ]
        if len(self.requests[identifier]) >= self.max_requests:
            return False
        self.requests[identifier].append(now)
        return True

    def cleanup(self):
        now = time.time()
        expired = [
            k for k, v in self.requests.items()
            if not any(now - ts < self.window_seconds for ts in v)
        ]
        for k in expired:
            del self.requests[k]

    def reset(self):
        self.requests.clear()


auth_rate_limiter = RateLimiter(max_requests=5, window_seconds=60)
api_rate_limiter = RateLimiter(max_requests=settings.RATE_LIMIT_MAX_REQUESTS, window_seconds=settings.RATE_LIMIT_WINDOW_SECONDS)


async def rate_limit_middleware(request: Request, call_next):
    client_ip = request.client.host if request.client else "unknown"

    if request.url.path.startswith("/api/v1/auth/token") or request.url.path.startswith("/api/v1/auth/register"):
        if not auth_rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )

    if request.url.path.startswith("/api/v1/"):
        if not api_rate_limiter.is_allowed(client_ip):
            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."}
            )

    response = await call_next(request)
    return response


async def exception_handler(request: Request, exc: Exception):
    logger.error(
        f"Unhandled exception on {request.method} {request.url.path}: {exc}",
        exc_info=True
    )
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "An internal server error occurred"}
    )


async def validation_exception_handler(request: Request, exc):
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": exc.errors() if hasattr(exc, 'errors') else str(exc)}
    )
