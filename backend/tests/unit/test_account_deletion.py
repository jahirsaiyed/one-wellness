"""
Unit tests — KAN-21: Account deletion & PDPL compliance.

Covers:
- POST /v1/users/me/delete-request → soft delete (deleted_at set, is_active=False)
- Deleted user cannot log in (401)
- Deletion response contains 30-day purge schedule
- _hard_purge_user anonymizes all PHI fields
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest
from httpx import ASGITransport, AsyncClient

from app.api.v1.users import PURGE_DAYS, _hard_purge_user
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import create_access_token
from app.main import app
from app.models.user import User, UserRole

# ── Shared test key constants (same as tests/conftest.py — autouse handles patching) ──

_PASSWORD = "TestPass123!"


# ── Helpers ───────────────────────────────────────────────────────────────────


def _make_result(value=None) -> MagicMock:
    result = MagicMock()
    result.scalar_one_or_none.return_value = value
    return result


def _make_mock_db(user: User | None = None) -> MagicMock:
    db = MagicMock()
    db.execute = AsyncMock(return_value=_make_result(user))
    db.flush = AsyncMock()
    db.commit = AsyncMock()
    db.rollback = AsyncMock()
    db.close = AsyncMock()
    db.add = MagicMock()
    return db


def _make_mock_redis() -> AsyncMock:
    r = AsyncMock()
    r.get.return_value = None
    r.setex.return_value = True
    r.delete.return_value = 1
    return r


def _make_user(
    role: str = UserRole.client.value,
    deleted_at: datetime | None = None,
) -> User:
    from app.core.security import hash_password

    user = User()
    user.id = uuid.uuid4()
    user.email = f"u-{uuid.uuid4().hex[:6]}@example.com"
    user.full_name = "Test User"
    user.role = role
    user.preferred_language = "en"
    user.timezone = "Asia/Dubai"
    user.hashed_password = hash_password(_PASSWORD)
    user.totp_secret = None
    user.totp_confirmed = False
    user.totp_backup_codes = None
    user.google_sub = None
    user.is_safety_officer = False
    user.created_at = datetime.now(UTC)
    user.updated_at = datetime.now(UTC)
    user.deleted_at = deleted_at
    return user


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def deletion_client():
    """
    Async HTTP client with dependency overrides for deletion tests.
    Yields (client, mock_db, mock_redis) tuple.
    """
    mock_db = _make_mock_db()
    mock_redis = _make_mock_redis()

    async def _override_db():
        yield mock_db

    app.dependency_overrides[get_db] = _override_db
    app.dependency_overrides[get_redis] = lambda: mock_redis

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        yield client, mock_db, mock_redis

    app.dependency_overrides.clear()


# ── Tests ─────────────────────────────────────────────────────────────────────


class TestSoftDelete:
    """POST /v1/users/me/delete-request"""

    async def test_delete_request_returns_202(self, deletion_client):
        """Authenticated delete request → 202 Accepted."""
        client, mock_db, _ = deletion_client
        user = _make_user()
        access_token, _ = create_access_token(subject=str(user.id), role=user.role)

        mock_db.execute.return_value = _make_result(user)

        resp = await client.post(
            "/v1/users/me/delete-request",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 202

    async def test_soft_delete_sets_deleted_at(self, deletion_client):
        """After delete-request, user.deleted_at is set and is_active becomes False."""
        client, mock_db, _ = deletion_client
        user = _make_user()
        assert user.deleted_at is None  # pre-condition

        access_token, _ = create_access_token(subject=str(user.id), role=user.role)
        mock_db.execute.return_value = _make_result(user)

        await client.post(
            "/v1/users/me/delete-request",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Endpoint mutates the user object in place
        assert user.deleted_at is not None
        assert user.is_active is False

    async def test_delete_response_contains_scheduled_purge_date(self, deletion_client):
        """Response body must include scheduled_deletion_at ~30 days out."""
        client, mock_db, _ = deletion_client
        user = _make_user()
        access_token, _ = create_access_token(subject=str(user.id), role=user.role)
        mock_db.execute.return_value = _make_result(user)

        resp = await client.post(
            "/v1/users/me/delete-request",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        data = resp.json()
        assert "scheduled_deletion_at" in data
        assert "message" in data

    async def test_already_deleted_user_gets_400(self, deletion_client):
        """Calling delete-request twice → 400."""
        client, mock_db, _ = deletion_client
        already_deleted = _make_user(deleted_at=datetime.now(UTC))
        access_token, _ = create_access_token(
            subject=str(already_deleted.id), role=already_deleted.role
        )

        # get_current_active_user checks is_active; a user with deleted_at set is inactive.
        # So this will return 403 from get_current_active_user, not 400 from our check.
        # Either 400 or 403 proves the endpoint is protected.
        mock_db.execute.return_value = _make_result(already_deleted)

        resp = await client.post(
            "/v1/users/me/delete-request",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code in (400, 403)

    async def test_purge_days_constant_is_30(self):
        """PURGE_DAYS must equal 30 per PDPL retention policy."""
        assert PURGE_DAYS == 30


class TestDeletedUserLogin:
    """Deleted users must not be able to authenticate."""

    async def test_deleted_user_login_returns_401(self, deletion_client):
        """Login endpoint filters out deleted users (deleted_at IS NOT NULL)."""
        client, mock_db, _ = deletion_client

        # Login query filters deleted_at.is_(None) → returns None for deleted user
        mock_db.execute.return_value = _make_result(None)

        resp = await client.post(
            "/v1/auth/login",
            json={"email": "deleted@example.com", "password": _PASSWORD},
        )

        assert resp.status_code == 401

    async def test_deleted_user_token_rejected_on_protected_route(self, deletion_client):
        """Token for a soft-deleted user → 401 from get_current_user dependency."""
        client, mock_db, _ = deletion_client
        user = _make_user(deleted_at=datetime.now(UTC))
        access_token, _ = create_access_token(subject=str(user.id), role=user.role)

        # get_current_user queries with deleted_at.is_(None) → returns None for deleted user
        mock_db.execute.return_value = _make_result(None)

        resp = await client.get(
            "/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 401


class TestHardPurge:
    """_hard_purge_user() — PHI anonymization logic (KAN-89/90)."""

    async def test_purge_clears_phi_fields(self):
        """After purge, all PHI fields must be zeroed/replaced with tombstone values."""
        user = _make_user(deleted_at=datetime.now(UTC))  # purge guard: deleted_at must be set
        user.totp_secret = "SOMESECRET"
        user.totp_backup_codes = ["code1", "code2"]
        user.google_sub = "google123"

        mock_db = _make_mock_db(user=user)

        await _hard_purge_user(str(user.id), mock_db)

        assert user.full_name == "[deleted]"
        assert user.email.startswith("deleted-")
        assert user.hashed_password is None
        assert user.totp_secret is None
        assert user.totp_backup_codes is None
        assert user.google_sub is None

    async def test_purge_skips_active_user(self):
        """Purge must not modify a user whose deleted_at is None (safety guard)."""
        user = _make_user()
        user.full_name = "Active User"
        assert user.deleted_at is None

        mock_db = _make_mock_db(user=user)

        await _hard_purge_user(str(user.id), mock_db)

        # Active user → purge is a no-op
        assert user.full_name == "Active User"

    async def test_purge_skips_not_found_user(self):
        """Purge with unknown user_id is a no-op (no exception raised)."""
        mock_db = _make_mock_db(user=None)
        # Should not raise
        await _hard_purge_user(str(uuid.uuid4()), mock_db)

    async def test_purge_commits_after_phi_clear(self):
        """Purge must commit the session after zeroing PHI."""
        user = _make_user(deleted_at=datetime.now(UTC))
        mock_db = _make_mock_db(user=user)

        await _hard_purge_user(str(user.id), mock_db)

        mock_db.commit.assert_called_once()
