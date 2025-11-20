from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.core.config import log_database_url
from app.core.database import Base, engine
from app.core.rate_limiter import RedisRateLimiter


def import_all_models() -> None:
    from app.models.auth_session import AuthSession  # type: ignore # noqa: F401
    from app.models.backup_code import BackupCode  # type: ignore # noqa: F401
    from app.models.user import User  # type: ignore # noqa: F401


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    # init rate limiter
    limiter = RedisRateLimiter()
    app.state.rate_limiter = limiter

    try:
        # Startup
        await limiter.init()
    except Exception as e:
        logger.error(f"Failed to initialize RedisRateLimiter: {e}")
        raise e

    try:
        # 1. Criar tabelas
        async with engine.begin() as conn:
            # import_all_models()
            await conn.run_sync(Base.metadata.create_all, checkfirst=True)
            log_database_url()
        print("✅ Database initialized")

        yield
    finally:
        # Shutdown logic
        logger.info("Shutting down application...")
        try:
            await limiter.close()
            logger.info("✅ Redis limiter connection closed.")
        except Exception as e:
            logger.error(f"❌ Failed to close Redis limiter: {e}")
        await engine.dispose()
        logger.info("✅ Database engine disposed.")
        logger.remove()  # Garante o flush final e o desligamento dos sinks do loguru
