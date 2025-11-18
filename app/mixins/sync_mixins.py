# app/models/mixins.py
from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import Mapped, mapped_column


class SyncMixin:
    sync_uuid: Mapped[str] = mapped_column(nullable=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    sync_enabled: Mapped[bool] = mapped_column(default=False)
