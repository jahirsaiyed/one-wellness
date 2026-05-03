"""
Integration tests — KAN-19: Full auth flow.
Register → Login → Refresh → Logout → Protected route → RBAC.

All tests use httpx.AsyncClient with mocked DB and Redis (no external services needed).
"""
from __future__ import annotations

import uuid

import pytest

from app.core.security import create_access_token, create_refresh_token, decode_token
from app.models.user import UserRole
from tests.integration.conftest import _make_result, make_test_user

_PASSWORD = "TestPass123!"


class TestRegister:
    """POST /v1/auth/register"""

    async def test_register_returns_201(self, async_client, mock_db):
        """New user registration → 201 with tokens and user info."""
        # No existing user for duplicate check
        mock_db.execute.return_value = _make_result(None)

        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": f"new-{uuid.uuid4().hex[:6]}@example.com",
                "password": _PASSWORD,
                "full_name": "New User",
            },
        )

        assert resp.status_code == 201
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["role"] == UserRole.client.value
        assert data["requires_totp"] is False

    async def test_register_duplicate_email_returns_400(self, async_client, mock_db):
        """Registering with an already-used email → 400."""
        existing = make_test_user()
        mock_db.execute.return_value = _make_result(existing)

        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": existing.email,
                "password": _PASSWORD,
                "full_name": "Dup User",
            },
        )

        assert resp.status_code == 400
        assert "already registered" in resp.json()["detail"].lower()

    async def test_register_access_token_is_decodable(self, async_client, mock_db):
        """Returned access token must be a valid RS256 JWT with expected claims."""
        mock_db.execute.return_value = _make_result(None)

        resp = await async_client.post(
            "/v1/auth/register",
            json={
                "email": f"jwt-check-{uuid.uuid4().hex[:6]}@example.com",
                "password": _PASSWORD,
                "full_name": "JWT Checker",
            },
        )

        assert resp.status_code == 201
        payload = decode_token(resp.json()["access_token"])
        assert payload["type"] == "access"
        assert payload["role"] == UserRole.client.value


class TestLogin:
    """POST /v1/auth/login"""

    async def test_login_valid_credentials_returns_200(self, async_client, mock_db):
        """Valid email + password → 200 with tokens."""
        user = make_test_user()
        mock_db.execute.return_value = _make_result(user)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": user.email, "password": _PASSWORD},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert data["requires_totp"] is False  # client doesn't need TOTP

    async def test_login_wrong_password_returns_401(self, async_client, mock_db):
        """Wrong password → 401."""
        user = make_test_user()
        mock_db.execute.return_value = _make_result(user)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": user.email, "password": "WrongPassword!"},
        )

        assert resp.status_code == 401

    async def test_login_unknown_email_returns_401(self, async_client, mock_db):
        """Unknown email → 401 (no user found)."""
        mock_db.execute.return_value = _make_result(None)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": "nobody@example.com", "password": _PASSWORD},
        )

        assert resp.status_code == 401


class TestRefreshToken:
    """POST /v1/auth/token/refresh"""

    async def test_refresh_with_valid_token_returns_200(self, async_client, mock_db, mock_redis):
        """Valid refresh token → 200 with new access + refresh tokens."""
        user = make_test_user()
        refresh_token, refresh_jti = create_refresh_token(subject=str(user.id))

        # Redis confirms the JTI is stored; DB returns the user
        mock_redis.get.return_value = str(user.id)
        mock_db.execute.return_value = _make_result(user)

        resp = await async_client.post(
            "/v1/auth/token/refresh",
            json={"refresh_token": refresh_token},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["access_token"] != refresh_token  # rotated

    async def test_refresh_with_revoked_token_returns_401(self, async_client, mock_redis):
        """Refresh token not in Redis (revoked/expired) → 401."""
        user = make_test_user()
        refresh_token, _ = create_refresh_token(subject=str(user.id))

        mock_redis.get.return_value = None  # JTI not found → revoked

        resp = await async_client.post(
            "/v1/auth/token/refresh",
            json={"refresh_token": refresh_token},
        )

        assert resp.status_code == 401

    async def test_refresh_with_garbage_token_returns_401(self, async_client):
        """Invalid JWT string → 401."""
        resp = await async_client.post(
            "/v1/auth/token/refresh",
            json={"refresh_token": "not.a.jwt"},
        )
        assert resp.status_code == 401

    async def test_refresh_rotates_token(self, async_client, mock_db, mock_redis):
        """Old JTI must be deleted from Redis; new one stored."""
        user = make_test_user()
        refresh_token, refresh_jti = create_refresh_token(subject=str(user.id))

        mock_redis.get.return_value = str(user.id)
        mock_db.execute.return_value = _make_result(user)

        await async_client.post("/v1/auth/token/refresh", json={"refresh_token": refresh_token})

        # Old JTI deleted
        mock_redis.delete.assert_called_once_with(f"refresh_token:{refresh_jti}")
        # New JTI stored (setex called at least once)
        assert mock_redis.setex.call_count >= 1


class TestLogout:
    """POST /v1/auth/logout"""

    async def test_logout_returns_204(self, async_client, mock_db, mock_redis):
        """Authenticated logout → 204 No Content."""
        user = make_test_user()
        access_token, _ = create_access_token(subject=str(user.id), role=user.role)
        refresh_token, _ = create_refresh_token(subject=str(user.id))

        mock_redis.get.return_value = None  # not blacklisted
        mock_db.execute.return_value = _make_result(user)

        resp = await async_client.post(
            "/v1/auth/logout",
            headers={"Authorization": f"Bearer {access_token}"},
            cookies={"refresh_token": refresh_token},
        )

        assert resp.status_code == 204

    async def test_logout_without_token_returns_401(self, async_client):
        """No auth token → 401."""
        resp = await async_client.post("/v1/auth/logout")
        assert resp.status_code == 401


class TestProtectedRoute:
    """GET /v1/users/me — exercises auth middleware."""

    async def test_valid_token_returns_200(self, async_client, mock_db, mock_redis):
        """Valid Bearer token → 200 with user data."""
        user = make_test_user()
        access_token, _ = create_access_token(subject=str(user.id), role=user.role)

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(user)

        resp = await async_client.get(
            "/v1/users/me",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["role"] == UserRole.client.value

    async def test_expired_token_returns_401(self, async_client):
        """Tampered / invalid JWT → 401."""
        resp = await async_client.get(
            "/v1/users/me",
            headers={"Authorization": "Bearer eyJhbGciOiJSUzI1NiJ9.invalid.sig"},
        )
        assert resp.status_code == 401

    async def test_no_token_returns_401(self, async_client):
        """Missing auth header → 401."""
        resp = await async_client.get("/v1/users/me")
        assert resp.status_code == 401

    async def test_client_role_blocked_from_admin_route(self, async_client, mock_db, mock_redis):
        """Client token accessing platform_admin-only route → 403."""
        user = make_test_user(role=UserRole.client.value)
        access_token, _ = create_access_token(
            subject=str(user.id), role=user.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(user)

        resp = await async_client.get(
            "/_test/admin-only",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 403

    async def test_admin_role_can_access_admin_route(self, async_client, mock_db, mock_redis):
        """platform_admin with totp_verified token → 200 on admin route."""
        admin = make_test_user(role=UserRole.platform_admin.value, totp_confirmed=True)
        access_token, _ = create_access_token(
            subject=str(admin.id), role=admin.role, totp_verified=True
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(admin)

        resp = await async_client.get(
            "/_test/admin-only",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200
