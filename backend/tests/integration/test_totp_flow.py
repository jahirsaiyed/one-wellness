"""
Integration tests — KAN-20: TOTP two-factor authentication flow.

Covers:
- Therapist login sets requires_totp=True in response
- TOTP-gated route rejects token without totp_verified claim
- Successful TOTP verification upgrades token to totp_verified=True
- Wrong TOTP code → 400
- Backup code consumption
"""
from __future__ import annotations

import pyotp
import pytest

from app.core.security import (
    create_access_token,
    decode_token,
    generate_backup_codes,
    generate_totp_secret,
)
from app.models.user import UserRole
from tests.integration.conftest import _make_result, make_test_user

_PASSWORD = "TestPass123!"


class TestTherapistLogin:
    """Login behavior for TOTP-required roles."""

    async def test_therapist_login_returns_requires_totp_true(
        self, async_client, mock_db, mock_redis
    ):
        """Therapist with confirmed TOTP → login returns 200 + requires_totp=True."""
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=True)
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": therapist.email, "password": _PASSWORD},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["requires_totp"] is True

    async def test_therapist_login_token_has_totp_verified_false(
        self, async_client, mock_db, mock_redis
    ):
        """Post-login token for therapist must have totp_verified=False until they verify."""
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=True)
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": therapist.email, "password": _PASSWORD},
        )

        assert resp.status_code == 200
        access_token = resp.json()["access_token"]
        payload = decode_token(access_token)
        assert payload["totp_verified"] is False

    async def test_client_login_does_not_require_totp(
        self, async_client, mock_db, mock_redis
    ):
        """Client role → login returns requires_totp=False."""
        client_user = make_test_user(role=UserRole.client.value)
        mock_db.execute.return_value = _make_result(client_user)

        resp = await async_client.post(
            "/v1/auth/login",
            json={"email": client_user.email, "password": _PASSWORD},
        )

        assert resp.status_code == 200
        assert resp.json()["requires_totp"] is False


class TestTOTPGatedRoute:
    """Routes using get_totp_verified_user dependency block unverified therapists."""

    async def test_therapist_without_totp_verified_gets_403(
        self, async_client, mock_db, mock_redis
    ):
        """Token with totp_verified=False for therapist → 403 on TOTP-gated route."""
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=True)
        # Token issued post-login (totp_verified not yet done)
        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.get(
            "/_test/totp-gated",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 403

    async def test_therapist_with_totp_verified_gets_200(
        self, async_client, mock_db, mock_redis
    ):
        """Token with totp_verified=True for therapist → 200 on TOTP-gated route."""
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=True)
        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=True
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.get(
            "/_test/totp-gated",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200

    async def test_client_passes_totp_gated_route(
        self, async_client, mock_db, mock_redis
    ):
        """Client role (requires_totp=False) always passes the TOTP check."""
        client_user = make_test_user(role=UserRole.client.value)
        access_token, _ = create_access_token(
            subject=str(client_user.id), role=client_user.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(client_user)

        resp = await async_client.get(
            "/_test/totp-gated",
            headers={"Authorization": f"Bearer {access_token}"},
        )

        # Client doesn't require TOTP so passes the check, but is blocked by nothing else
        assert resp.status_code == 200


class TestTOTPVerify:
    """POST /v1/auth/totp/verify"""

    async def test_valid_totp_code_returns_200_with_verified_token(
        self, async_client, mock_db, mock_redis
    ):
        """Valid TOTP code → 200, access token with totp_verified=True."""
        secret = generate_totp_secret()
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=False)
        therapist.totp_secret = secret

        # Token issued post-login (totp_verified=False)
        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        valid_code = pyotp.TOTP(secret).now()
        resp = await async_client.post(
            "/v1/auth/totp/verify",
            json={"code": valid_code},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200
        data = resp.json()
        assert data["verified"] is True

        # Upgraded token must have totp_verified=True
        upgraded_payload = decode_token(data["access_token"])
        assert upgraded_payload["totp_verified"] is True

    async def test_wrong_totp_code_returns_400(
        self, async_client, mock_db, mock_redis
    ):
        """Invalid TOTP code → 400."""
        secret = generate_totp_secret()
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=False)
        therapist.totp_secret = secret

        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.post(
            "/v1/auth/totp/verify",
            json={"code": "000000"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 400

    async def test_totp_not_set_up_returns_400(
        self, async_client, mock_db, mock_redis
    ):
        """User without totp_secret calling /totp/verify → 400."""
        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=False)
        therapist.totp_secret = None  # no secret yet

        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.post(
            "/v1/auth/totp/verify",
            json={"code": "123456"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 400
        assert "setup" in resp.json()["detail"].lower()

    async def test_valid_backup_code_returns_200(
        self, async_client, mock_db, mock_redis
    ):
        """Valid backup code → 200 + token upgraded, backup code consumed."""
        plain_codes, hashed_codes = generate_backup_codes()
        secret = generate_totp_secret()

        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=True)
        therapist.totp_secret = secret
        therapist.totp_backup_codes = hashed_codes[:]  # copy so we can compare later

        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        backup_code = plain_codes[0]
        resp = await async_client.post(
            "/v1/auth/totp/verify",
            json={"code": backup_code},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 200
        assert resp.json()["verified"] is True
        # Backup code must be consumed (one fewer code)
        assert len(therapist.totp_backup_codes) == len(hashed_codes) - 1

    async def test_wrong_backup_code_returns_400(
        self, async_client, mock_db, mock_redis
    ):
        """Invalid backup code (not in list) → 400."""
        _, hashed_codes = generate_backup_codes()
        secret = generate_totp_secret()

        therapist = make_test_user(role=UserRole.therapist.value, totp_confirmed=True)
        therapist.totp_secret = secret
        therapist.totp_backup_codes = hashed_codes[:]

        access_token, _ = create_access_token(
            subject=str(therapist.id), role=therapist.role, totp_verified=False
        )

        mock_redis.get.return_value = None
        mock_db.execute.return_value = _make_result(therapist)

        resp = await async_client.post(
            "/v1/auth/totp/verify",
            json={"code": "XXXX-YYYY"},
            headers={"Authorization": f"Bearer {access_token}"},
        )

        assert resp.status_code == 400
