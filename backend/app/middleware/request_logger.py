"""
Logs every HTTP request with method, path, status code, and wall-clock latency.
Skips /health and /docs to keep noise low.
"""
import time
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger("nexa.http")

_SKIP_PATHS = {"/health", "/docs", "/openapi.json", "/redoc"}


class RequestLoggerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        if request.url.path in _SKIP_PATHS:
            return await call_next(request)

        t0 = time.perf_counter()
        response = await call_next(request)
        latency_ms = int((time.perf_counter() - t0) * 1000)

        logger.info(
            "%s %s → %d  (%dms)",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
        )
        return response
