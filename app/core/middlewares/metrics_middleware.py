import time

from fastapi.routing import APIRoute
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.metrics import (
    CORS_ALLOWED,
    CORS_BLOCKED,
    HTTP_REQUEST_COUNT,
    HTTP_REQUEST_TIME,
)

ALLOWED_ORIGINS = {
    "https://zenndi.com.br",
    "https://app.zenndi.com.br",
    "http://localhost:3000",
}


def normalize_origin(origin: str | None):
    if not origin:
        return "no-origin"
    if origin in ALLOWED_ORIGINS:
        return origin.replace("https://", "").replace("http://", "")
    return "other"


# ============================================================
# MIDDLEWARE DE MÉTRICAS
# ============================================================


class MetricsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        start = time.time()

        # Detectar rota real
        route: APIRoute | None = request.scope.get("route")
        route_path = route.path if route else "unknown"

        method = request.method

        # ---- CORS MÉTRICAS ----
        origin = request.headers.get("origin")
        origin_norm = normalize_origin(origin)

        if origin and origin_norm != "other":
            CORS_ALLOWED.labels(origin=origin_norm).inc()
        else:
            CORS_BLOCKED.labels(origin=origin_norm).inc()

        # ---- Seguir requisição ----
        try:
            response = await call_next(request)
        except Exception:
            duration = time.time() - start
            HTTP_REQUEST_TIME.labels(method, route_path, "500").observe(duration)
            HTTP_REQUEST_COUNT.labels(method, route_path, "500").inc()
            raise

        # ---- Registrar métricas de HTTP ----
        duration = time.time() - start
        status = str(response.status_code)

        HTTP_REQUEST_TIME.labels(method, route_path, status).observe(duration)
        HTTP_REQUEST_COUNT.labels(method, route_path, status).inc()

        return response
