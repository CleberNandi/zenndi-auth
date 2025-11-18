import importlib
import pkgutil
from types import ModuleType
from typing import TYPE_CHECKING, cast

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_fastapi_instrumentator import Instrumentator
from sentry_sdk.integrations.fastapi import FastApiIntegration
from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration

from app.api import v1 as endpoints
from app.core.config import settings
from app.core.lifespan import lifespan
from app.core.logging import setup_logging
from app.core.middlewares.logging_middleware import LoggingMiddleware

logger = setup_logging()

# --- Sentry Initialization ---
SENTRY_DSN = settings.get("SENTRY_DSN")
if SENTRY_DSN:
    sentry_sdk.init(
        dsn=SENTRY_DSN,
        integrations=[FastApiIntegration(), SqlalchemyIntegration()],
        traces_sample_rate=settings.get("SENTRY_TRACES_SAMPLE_RATE", 0.2),
        environment=settings.get("ENV_MODE", "development"),
    )
    logger.info("✅ Sentry SDK inicializado.")

if TYPE_CHECKING:
    from enum import Enum

app = FastAPI(
    title="zenndi auth api",
    description="Authentication API for Zenndi platform",
    version="1.0.0",
    lifespan=lifespan,
    contact={
        "name": "Zenndi Support",
        "url": "https://zenndi.com/support",
        "email": "suporte@zenndi.nandidigtalworks.com.br",
    },
)

origins = settings.ALLOWED_ORIGINS if not settings.ALLOW_ORIGINS_DEV else ["*"]

# Middlewares
app.add_middleware(LoggingMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
    expose_headers=[
        "X-RateLimit-Limit",
        "X-RateLimit-Remaining",
        "Retry-After",
        "X-Request-ID",
    ],
    max_age=600,
)
# Instrumentação do Prometheus
# Unifica as métricas do instrumentador com as suas métricas customizadas
Instrumentator(
    should_instrument_requests_inprogress=True,
).instrument(app).expose(app, endpoint="/metrics", include_in_schema=False)


def include_all_routers(
    app: FastAPI, package: ModuleType, api_version: str = "v1"
) -> None:
    """
    Inclui todos os routers dinamicamente da estrutura app/api/{version}/endpoints/

    Args:
        app: FastAPI instance
        package: Módulo dos endpoints (app.api.v1.endpoints)
        api_version: Versão da API (default: v1)
    """
    for _, module_name, _ in pkgutil.iter_modules(package.__path__):
        try:
            module = importlib.import_module(f"{package.__name__}.{module_name}.routes")
            if hasattr(module, "router"):
                prefix = f"/api/{api_version}/{module_name}"
                tags = cast("list[str | Enum]", [module_name.capitalize()])
                app.include_router(module.router, prefix=prefix, tags=tags)
                print(f"✅ Router incluído: {prefix}")  # Log para debug
        except ModuleNotFoundError as e:
            print(f"⚠️  Router não encontrado: {module_name} - {e}")
            continue


include_all_routers(app, endpoints)
