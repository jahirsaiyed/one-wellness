"""
Unit tests — KAN-80: JWT generation/validation, RBAC guards, password hashing.
KAN-86: TOTP verification logic.
KAN-91: Deletion/soft-delete behaviour.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    generate_backup_codes,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    verify_backup_code,
    verify_password,
    verify_totp_code,
)
from app.models.user import User, UserRole


# ── Password hashing ──────────────────────────────────────────────────────────


def test_hash_and_verify_password():
    plain = "SecurePass123!"
    hashed = hash_password(plain)
    assert hashed != plain
    assert verify_password(plain, hashed)


def test_wrong_password_rejected():
    hashed = hash_password("CorrectHorse")
    assert not verify_password("WrongHorse", hashed)


# ── JWT access token ──────────────────────────────────────────────────────────


RSA_PRIVATE = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEA2a2rwplBQLzHPZe5RJr9vZPZ0KGSS5JBkbJJRuXOnaHFOBmL
B5F9RJcRKrAMLNg9PvU7RRzOlEHBfO+GnHMEJLJTrM3TjLR9KFJUNi98cSwVGq6C
VKyHvg4Ja6TqpJMt3KqMzjz+1hv3wqT0OZA4BuDKC8V+9O7D0m0VRsF4VSPXW2rl
wFbezjFbkLxg/nX1RvBUTVdA8ErmqV9JqXvLSh7pCNsM5K1MNXnLmDgHAnzJnTwh
V5W+4j3INfHlBt5RPIm+qs0kqC6MqXSGuwpXd2aSJJDhSjOMsXNEpMNWD1GRW0qo
TYmgFTr37wdqJxq9GhN3VxMM5N+LovYtasQfawIDAQABAoIBAHbIBm8OkJVNrr88
F7e4SBAAH6eDZRSECdDMhGvKBqkLj59cP9A0o7W0FJn1Sp9E4rZGHmMGa1VkH9eR
g8VY+2u0u1yxIu0EiEX6f7j5L2wP/OQHS7L6zX7M/s0oBxVhm5ZAO/kWMdj7z5bP
q1vZ+Tc5jMkj4B4L8Jj2Pz2DCSSP0eO3pEBW5hGiG3IH1SdLJJEiY5A2xpzGkbp+
8zHPQpj0SNXFV1kHo9/T6BJ/2W1m5rCE4Fv7zCz5R5VW7fJ4D+KDXN0nXJz2R8bj
TM6cBoUG/1E+YzAa9VnHCY4eZlkl3pFnR2v0hHlHg8Jz6gNrqjZCiIJH0bQbK+i6
6YPh0AECgYEA7Cz8pGe6uB2lOT2Y9NvkLKCFHV5s5Y8lG/GxA1P8MmZTlHKQ0Nnh
b0JJ0VNEe9a2g8RUa3RX1WNz7YYQN5l7HXKNTaQmJ5HzJqQ0FJv+RVQV4KE6TM2p
8V7Y1mC5d4JjGmWH2jJKh2HpZJaJ5nFWH01a2U2qz0YzQ4HxhkECgYEA7HyxVq7P
N9Hl5Lk7mG7aH8vJ6Rz9a8FEW3+z3Jv9YLq4hHLQkJ3Cv7l5QqXFQ1qZWjM/6Ew
7Qz3d5TgCMtNGkX5q9TQz5l7Gd9q7E6Jq4Ks+nXf9B2H7KVJzL6E0P7Nh4QRGZW
XyZNtRjJNGkBlz5JqKvQlLHcPYyoH4sCgYEAsMCEhYqRoiXxB7P7H3KN8j5s3GnC
8Z4mBH2KVy7r0DtHC3s+8vHlgRQpNQr0H8BNXJF8vJqT3EL0T3wZ7H5SZ1rNX6Ol
OVdJ7LF7vRjJqF7HQ3jXl9r7JkCCrXkFsVznYJeN0hN3jJv0kHQ/IWfPE9HJv9KT
TYp8pgMGH4ECgYBGT/M3uB2q0MCsFQq0TJfM5n7HxFKwXpTQ9a8G8mSvR0q7kYJN
WkPMb2N2DFqE7gBT9qBajN7c8FxJRFqLGN4P2BwGZcKb4NLXJK9Fv6RpHJD3nMKs
PrXhbFz8R1K+Yl9EJkr1bkZbT3JjCk0D1nJqL2VNgPb3O7k7ZS9N6wKBgCpCGKmj
nQ9Rg5SV6R7F/5Hf7nJv0W7FN8K+z0W3jRn0Mv3QoqK3jFR0P5bfnzL7pX3N0JkV
Q5A8hLJ9B7N/kQZKJJ9M3P8v2J6K7bLV+s3JKJM9v6XhNQ8Fa8Hq+B1r/5L0R6X
FtGHK5JmEQzFRvJT1v4L5Qe/8GgZ89zk
-----END RSA PRIVATE KEY-----"""

RSA_PUBLIC = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2a2rwplBQLzHPZe5RJr9
vZPZ0KGSS5JBkbJJRuXOnaHFOBmLB5F9RJcRKrAMLNg9PvU7RRzOlEHBfO+GnHME
JLJTrM3TjLR9KFJUNi98cSwVGq6CVKyHvg4Ja6TqpJMt3KqMzjz+1hv3wqT0OZA4
BuDKC8V+9O7D0m0VRsF4VSPXW2rlwFbezjFbkLxg/nX1RvBUTVdA8ErmqV9JqXvL
Sh7pCNsM5K1MNXnLmDgHAnzJnTwhV5W+4j3INfHlBt5RPIm+qs0kqC6MqXSGuwpX
d2aSJJDhSjOMsXNEpMNWD1GRW0qoTYmgFTr37wdqJxq9GhN3VxMM5N+LovYtasQf
awIDAQAB
-----END PUBLIC KEY-----"""


@pytest.fixture(autouse=True)
def patch_keys(monkeypatch):
    monkeypatch.setattr("app.core.security._load_private_key", lambda: RSA_PRIVATE)
    monkeypatch.setattr("app.core.security._load_public_key", lambda: RSA_PUBLIC)


def test_access_token_roundtrip():
    user_id = str(uuid.uuid4())
    token, jti = create_access_token(subject=user_id, role="client")
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["role"] == "client"
    assert payload["type"] == "access"
    assert payload["jti"] == jti


def test_refresh_token_roundtrip():
    user_id = str(uuid.uuid4())
    token, jti = create_refresh_token(subject=user_id)
    payload = decode_token(token)
    assert payload["sub"] == user_id
    assert payload["type"] == "refresh"
    assert payload["jti"] == jti


def test_access_and_refresh_have_different_jtis():
    uid = str(uuid.uuid4())
    _, a_jti = create_access_token(subject=uid, role="client")
    _, r_jti = create_refresh_token(subject=uid)
    assert a_jti != r_jti


def test_totp_verified_claim_in_token():
    uid = str(uuid.uuid4())
    token, _ = create_access_token(subject=uid, role="therapist", totp_verified=True)
    payload = decode_token(token)
    assert payload["totp_verified"] is True


# ── RBAC / User model ─────────────────────────────────────────────────────────


def test_therapist_requires_totp():
    user = User()
    user.role = UserRole.therapist.value
    assert user.requires_totp is True


def test_admin_requires_totp():
    user = User()
    user.role = UserRole.platform_admin.value
    assert user.requires_totp is True


def test_client_does_not_require_totp():
    user = User()
    user.role = UserRole.client.value
    assert user.requires_totp is False


def test_hr_admin_does_not_require_totp():
    user = User()
    user.role = UserRole.hr_admin.value
    assert user.requires_totp is False


def test_soft_deleted_user_is_inactive(deleted_user):
    assert not deleted_user.is_active


def test_active_user_is_active(client_user):
    assert client_user.is_active


# ── TOTP ──────────────────────────────────────────────────────────────────────


def test_totp_secret_generation():
    secret = generate_totp_secret()
    assert len(secret) >= 16
    assert secret.isalnum()


def test_totp_uri_contains_issuer():
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, "user@example.com")
    assert "GCCWellness" in uri
    assert "user%40example.com" in uri or "user@example.com" in uri


def test_valid_totp_code_accepted():
    import pyotp
    secret = generate_totp_secret()
    code = pyotp.TOTP(secret).now()
    assert verify_totp_code(secret, code)


def test_invalid_totp_code_rejected():
    secret = generate_totp_secret()
    assert not verify_totp_code(secret, "000000")


# ── Backup codes ──────────────────────────────────────────────────────────────


def test_backup_code_generation():
    plain, hashed = generate_backup_codes()
    assert len(plain) == 8
    assert len(hashed) == 8
    for p in plain:
        assert "-" in p


def test_backup_code_verification():
    plain, hashed = generate_backup_codes()
    code = plain[3]
    idx = verify_backup_code(code, hashed)
    assert idx == 3


def test_wrong_backup_code_rejected():
    _, hashed = generate_backup_codes()
    assert verify_backup_code("XXXX-YYYY", hashed) is None


def test_backup_code_case_insensitive():
    plain, hashed = generate_backup_codes()
    code = plain[0].lower()
    idx = verify_backup_code(code, hashed)
    assert idx == 0
