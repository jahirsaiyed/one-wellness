from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class UserRole(str, enum.Enum):
    client = "client"
    therapist = "therapist"
    hr_admin = "hr_admin"
    platform_admin = "platform_admin"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(Text, nullable=False, unique=True, index=True)
    hashed_password: Mapped[str | None] = mapped_column(Text, nullable=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), nullable=False, default=UserRole.client.value, index=True
    )
    preferred_language: Mapped[str] = mapped_column(
        String(2), nullable=False, default="en"
    )
    timezone: Mapped[str] = mapped_column(Text, nullable=False, default="Asia/Dubai")

    # 2FA (KAN-20)
    totp_secret: Mapped[str | None] = mapped_column(Text, nullable=True)
    totp_confirmed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    totp_backup_codes: Mapped[list[str] | None] = mapped_column(
        ARRAY(Text), nullable=True
    )

    # Google OAuth2
    google_sub: Mapped[str | None] = mapped_column(Text, nullable=True, unique=True)

    # Sub-role flag
    is_safety_officer: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        onupdate=func.now(),
    )
    # Soft delete — triggers 30-day async purge (KAN-21)
    deleted_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    @property
    def is_active(self) -> bool:
        return self.deleted_at is None

    @property
    def requires_totp(self) -> bool:
        """Therapists and platform admins must complete TOTP before accessing protected routes."""
        return self.role in (UserRole.therapist.value, UserRole.platform_admin.value)
