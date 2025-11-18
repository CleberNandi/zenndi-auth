from datetime import UTC, datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base
from app.mixins.mixins import Mixins

if TYPE_CHECKING:
    from app.models.auth_session import AuthSession
    from app.models.backup_code import BackupCode


class User(Base, Mixins):
    __tablename__ = "users"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)

    # Campos de 2FA
    totp_secret: Mapped[Optional[str]] = mapped_column(String(255))
    is_2fa_enabled: Mapped[bool] = mapped_column(Boolean, default=False)

    # Campos de segurança
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verification_token: Mapped[Optional[str]] = mapped_column(String(255))

    # Controle de login
    failed_login_attempts: Mapped[int] = mapped_column(Integer, default=0)
    locked_until: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_login: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    password_changed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True)
    )

    # Plano
    plan: Mapped[Optional[str]] = mapped_column(String(20))

    # Relacionamentos
    auth_sessions: Mapped[list["AuthSession"]] = relationship(
        "AuthSession",
        back_populates="usuario",
        cascade="all, delete-orphan",
        passive_deletes=True,
    )
    backup_codes: Mapped[list["BackupCode"]] = relationship(
        "BackupCode", back_populates="usuario", cascade="all, delete-orphan"
    )

    # -------- Métodos utilitários --------
    @property
    def is_locked(self) -> bool:
        """Verifica se a conta está bloqueada."""
        return bool(self.locked_until and datetime.now(UTC) < self.locked_until)

    def reset_failed_attempts(self) -> None:
        """Reseta tentativas de login falhadas."""
        self.failed_login_attempts = 0
        self.locked_until = None
