import asyncio
import logging
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from alembic import context

# CORREÇÃO: Adiciona o diretório raiz ao Python path
root_dir = Path(__file__).parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

# Agora pode importar os models e settings
try:
    from app import models  # noqa: F401
    from app.core.config import settings
    from app.core.database import Base
except ImportError as e:
    print(f"❌ Erro ao importar módulos: {e}")
    print(f"🔍 Python path atual: {sys.path}")
    print(f"🔍 Diretório de trabalho: {os.getcwd()}")
    print(f"🔍 Conteúdo do diretório atual: {os.listdir('.')}")
    if os.path.exists("app"):
        print(f"🔍 Conteúdo do diretório app: {os.listdir('app')}")
    raise

# Config Alembic
config = context.config
fileConfig(config.config_file_name)
logger = logging.getLogger("alembic.env")

# DATABASE_URL já expandido pelo Dynaconf
# Montar DATABASE_URL dinamicamente
DATABASE_URL = f"postgresql+asyncpg://{settings.POSTGRES_USER}:{settings.POSTGRES_PASSWORD}@{settings.POSTGRES_HOST}:5432/{settings.POSTGRES_DB}"

if settings.ENV_MODE == "test":
    DATABASE_URL = "sqlite+aiosqlite:///:memory:"

# Metadata alvo
target_metadata = Base.metadata


def mask_db_url(url: str) -> str:
    """Remove senha da URL para exibir no log."""
    if "@" in url and "://" in url:
        prefix, rest = url.split("://", 1)
        if "@" in rest and ":" in rest.split("@")[0]:
            user, rest_after_user = rest.split("@", 1)
            user_no_pass = user.split(":")[0]
            return f"{prefix}://{user_no_pass}:***@{rest_after_user}"
    return url


def validate_env_and_db() -> None:
    """Evita rodar migrations no banco errado."""
    is_sqlite = DATABASE_URL.startswith("sqlite")
    is_postgres = DATABASE_URL.startswith("postgres")

    if settings.ENV_MODE == "prod" and not is_postgres:
        message = "🚫 Produção só pode rodar migrations em PostgreSQL."
        raise RuntimeError(message)
    if settings.ENV_MODE == "test" and not is_sqlite:
        message = "🚫 Testes só podem rodar migrations em SQLite (in-memory)."
        raise RuntimeError(message)


def run_migrations_offline() -> None:
    """Migrations no modo offline (sempre Postgres)."""
    validate_env_and_db()
    logger.info(
        f"[Alembic] OFFLINE | ENV_MODE: {settings.ENV_MODE} | Banco: {mask_db_url(DATABASE_URL)}"
    )
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    validate_env_and_db()
    logger.info(
        f"[Alembic] ONLINE | ENV_MODE: {settings.ENV_MODE} | Banco: {mask_db_url(DATABASE_URL)}"
    )
    connectable = create_async_engine(
        DATABASE_URL, poolclass=pool.NullPool, future=True
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
