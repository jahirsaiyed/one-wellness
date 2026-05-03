"""
Integration test fixtures — async HTTP client, mock DB session, mock Redis.
Shared by test_auth_flow.py, test_totp_flow.py, test_docker_health.py.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import Depends
from httpx import ASGITransport, AsyncClient

from app.api.deps import get_totp_verified_user, require_roles
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import hash_password
from app.main import app
from app.models.user import User, UserRole

# ── Cached test password hash (bcrypt is slow; compute once per session) ─────

_TEST_PASSWORD = "TestPass123!"
_TEST_PASSWORD_HASH = hash_password(_TEST_PASSWORD)


# ── Test-only routes (registered once at import time) ─────────────────────────

@app.get("/_test/admin-only", include_in_schema=False)
async def _test_admin_route(user: User = Depends(require_roles(UserRole.platform_admin))):
    return {"ok": True, "user_id": str(user.id)}


@app.get("/_test/totp-gated", include_in_schema=False)
async def _test_totp_gated_route(user: User = Depends(get_totp_verified_user)):
    return {"ok": True, "user_id": str(user.id)}


# ── Mock helpers ──────────────────────────────────────────────────────────────


def _make_result(value=None) -> MagicMock:
    """Wrap a value in a mock SQLAlchemy execute result."""
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def make_test_user(
    password: str = _TEST_PASSWORD,
    role: str = UserRole.client.value,
    totp_confirmed: bool = False,
    deleted_at: datetime | None = None,
) -> User:
    """Build an in-memory User with a known hashed password (no DB required)."""
    user = User()
    user.id = uuid.uuid4()
    user.email = f"test-{uuid.uuid4().hex[:6]}@example.com"
    user.full_name = "Test User"
    user.role = role
    user.preferred_language = "en"
    user.timezone = "Asia/Dubai"
    user.hashed_password = _TEST_PASSWORD_HASH if password == _TEST_PASSWORD else hash_password(password)
    user.totp_secret = None
    user.totp_confirmed = totp_confirmed
    user.totp_backup_codes = None
    user.google_sub = None
    user.is_safety_officer = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = deleted_at
    return user


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
def mock_db() -> MagicMock:
    """
    Realistic mock of an async SQLAlchemy session.
    - execute() is async, returns _make_result(None) by default
    - add() is sync, auto-sets obj.id if None (simulates flush default)
    - flush/commit/rollback/close are async no-ops
    """
    db = MagicMock()
    db.execute = AsyncMock(return_value=_make_result(None))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()

    def _fake_add(obj: object) -> None:
        if hasattr(obj, "id") and obj.id is None:
            obj.id = uuid.uuid4()

    db.add = MagicMock(side_effect=_fake_add)
    return db


@pytest.fixture
def mock_redis() -> AsyncMock:
    """Async mock Redis with sane defaults (no blacklisted tokens, setex/delete succeed)."""
    r = AsyncMock()
    r.get.return_value = None   # tokens not blacklisted / not stored by default
    r.setex.return_value = True
    r.delete.return_value = 1
    r.ping.return_value = True
    return r


@pytest.fixture
async def async_client(mock_db: MagicMock, mock_redis: AsyncMock):
    """
    httpx.AsyncClient wired to the FastAPI app with DB and Redis overridden.
    Dependency overrides are cleared after each test.
    """
    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client

    app.dependency_overrides.clear()
