"""
Pytest fixtures for Sprint 1 tests.
KAN-80: Unit tests for JWT, RBAC, password hashing.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.models.user import User, UserRole


# ── Mock user factories ───────────────────────────────────────────────────────


def make_user(
    role: str = UserRole.client.value,
    totp_confirmed: bool = False,
    deleted_at: datetime | None = None,
) -> User:
    user = User()
    user.id = uuid.uuid4()
    user.email = f"test-{uuid.uuid4().hex[:6]}@example.com"
    user.full_name = "Test User"
    user.role = role
    user.preferred_language = "en"
    user.timezone = "Asia/Dubai"
    user.totp_secret = None
    user.totp_confirmed = totp_confirmed
    user.totp_backup_codes = None
    user.google_sub = None
    user.is_safety_officer = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = deleted_at
    user.hashed_password = None
    return user


@pytest.fixture
def client_user() -> User:
    return make_user(role=UserRole.client.value)


@pytest.fixture
def therapist_user() -> User:
    return make_user(role=UserRole.therapist.value, totp_confirmed=True)


@pytest.fixture
def admin_user() -> User:
    return make_user(role=UserRole.platform_admin.value, totp_confirmed=True)


@pytest.fixture
def deleted_user() -> User:
    return make_user(deleted_at=datetime.now(UTC))


@pytest.fixture
def mock_redis():
    r = AsyncMock()
    r.get.return_value = None
    r.setex.return_value = True
    r.delete.return_value = True
    return r


@pytest.fixture
def mock_db():
    return AsyncMock()
