from datetime import UTC, datetime
from typing import Any

from sqlalchemy import event, func
from sqlalchemy.dialects.postgresql import TIMESTAMP
from sqlalchemy.engine import Connection
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.orm.mapper import Mapper


class Mixins:
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime | None] = mapped_column(
        default=func.now(),
        onupdate=func.now(),
        nullable=True
    )
    deleted_at: Mapped[datetime | None] = mapped_column(
        TIMESTAMP(timezone=True), nullable=True
    )
    is_active: Mapped[bool] = mapped_column(default=True)
    origin: Mapped[str] = mapped_column(default="api", nullable=False)


# Evento global que vale para todas as classes que herdarem de Mixins
@event.listens_for(Mixins, "before_update", propagate=True)
def set_deleted_at(mapper: Mapper[Any], connection: Connection, target: Mixins) -> None:
    """
    Se ativo for marcado como False e ainda não tiver deleted_at,
    seta automaticamente a data de deleção.
    """
    if target.is_active is False and target.deleted_at is None:
        target.deleted_at = datetime.now(UTC)
    elif target.is_active is True and target.deleted_at is not None:
        target.deleted_at = None
