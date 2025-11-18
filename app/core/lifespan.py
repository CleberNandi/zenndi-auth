from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.core.config import log_database_url
from app.core.database import Base, engine
from app.core.rate_limiter import RedisRateLimiter

# from seeds.seed_all import run_all_seeds


def import_all_models() -> None:
    from app.models.auth_session import AuthSession  # type: ignore # noqa: F401
    from app.models.backup_code import BackupCode  # type: ignore # noqa: F401
    from app.models.user import User  # type: ignore # noqa: F401


#     from app.models.categoria import Categoria  # type: ignore # noqa: F401
#     from app.models.orcamento import Orcamento  # type: ignore # noqa: F401
#     from app.models.fatura import Fatura  # type: ignore # noqa: F401
#     from app.models.fatura import FaturaPagamento  # type: ignore # noqa: F401
#     from app.models.cartao import Cartao  # type: ignore # noqa: F401
#     from app.models.conta import Conta  # type: ignore # noqa: F401
#     from app.models.transacao import Transacao  # type: ignore # noqa: F401
#     from app.models.transacao_parcela import TransacaoParcela  # type: ignore # noqa: F401
#     from app.models.auth_session import AuthSession  # type: ignore # noqa: F401
#     from app.models.backup_code import BackupCode  # type: ignore # noqa: F401
#     from app.models.auditoria import Auditoria  # type: ignore # noqa: F401
#     from app.models.banco import Banco  # type: ignore # noqa: F401
#     from app.models.login_attempt import LoginAttempt  # type: ignore # noqa: F401
#     from app.models.nfce import NFCe  # type: ignore # noqa: F401
#     from app.models.nfce_itens import NFCeItens  # type: ignore # noqa: F401


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
            await conn.run_sync(Base.metadata.create_all)
            log_database_url()
        print("✅ Database initialized")

        # 2. Rodar todos os seeds
        # async with AsyncSession(engine) as session:
        #     await run_all_seeds(session)

        yield
    finally:
        # Shutdown
        logger.remove()  # Garante o desligamento dos sinks do loguru
        await engine.dispose()
        print("🔒 Database engine disposed and logger shutdown.")
    
    # shutdown
    try:
        await limiter.close()
    except Exception:
        logger.exception("Failed to close limiter")
