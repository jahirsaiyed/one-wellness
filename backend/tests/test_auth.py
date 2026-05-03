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
MIIEowIBAAKCAQEAoVNhyYkByaNZdOQGVR58tRKdbpO4vEzUaqm2P7lhARJccr1m
bCDxw7iIt69jIl/88hviJnWf5W+LuPDr6egpN7WPuZb1lvhVK+sie4P3NpsnBn8D
G/By/sypBqe6yFB8i28OpF3636fhxHm6RbJSNM4foDdlPXgnAAyrm2Z7QPBTfLqm
LemcmvPsO0B5LRNORvxzoHlKqgAUgd2siR5aSSRp5gmxRXGwfwMyaUsPajLuRaE5
c9ddySwjbXLpqUUZggewaTkm16PQ2W3MqPtQaKSDdAbDDoB/b+UbaBlUeqT2U3fT
rRQRMua1rKx/ueLx5ZNaKVfdOqprJe80Q+VfvwIDAQABAoIBAAGaTZFOG9pWfDfv
YGnt3+kZ0osu/lNa/UAQCCz+GP4ebuFLvp3aMYmAJrxe12b+ICO01JxzZ7X37TuJ
o5zGMmUIyz3Zrf5X4KfxvpZ09OEYgOmm6MkZLIzmfwYymjLz31p9Rt52k1yWE0w7
gpCMGUmU0Ko4hd6qxNLSmjPbIuQkWw4V1KDqWs3xVUZdTbD5GKUugroQ5HxXWCBH
SbYfSZkodUjrsmOAzkh3Tz0vPA+Kiqj9TVZdEboEa8qNehUDYP3SWXVf+JRnkWrj
4ysqSzOijprwvAJ6dumUXabzhkyYqwkf5boVjO2rUS1G3ik2/vKXTLJMrJp22Id0
zA7pfDUCgYEAzthmsm3bO/Xsj7pyzb3YnpwjOQAzS959uOK2bfYVBsn8S8eHzvTe
A/hgOVthU7dCKbW68RvVHjcU51lpI8ZUnv5tfPvEyEU6/EjWTOpC5Oilm5QmyRlL
n/Gis1RZVu4a7cn9QEiJP79meEhxIounb9KGftG2pSR2o0PG7jFu/hsCgYEAx6nC
bjU7CPdipqhxzPtnL+RtdG7NvYOBi4qfrf9v0gEevjsPOpV22/RgU6VCOGzqAS2o
lPz8HlopZXOD14tQkfKKt6UJ6fbPIJVEyjtprcdp39rJi6BUNpC/WNCkpP8V6huS
Ydv1zDbQtK9Z5jX+vLPr1aQ7nrspXTZx6Sjvby0CgYEAu3XOJRmA3mez3FLK5wGO
h7jUBz3SP4lGAcCeOywRxFRcrkUIJR0w9QIuGu1hWKC2etyzrv5deIPNExqqOfzu
BiZqDiKTJjnwCmLsrUqGE7VxGX38ZLbjHfK9VK82RJ2IlEdCmPbkRHzvnkVxGzDc
L3Dp6ZegYyyXxMGRUaBFik8CgYBvGjOrB8vV7XLjsg/BNJPyvnV5uL6bmjXX5Ed+
lwkuHplw2YRb4RfGxXFkmi0DIPgFt9Z7MVtJuHoYjfLrWgZ3cDNohVnC6yfOxcEF
l5HytWhgvGoyXAEAbANN9KvpdFhJcRY/hhp8jHQOVxT7WUhq0OOGemECrrsRt14j
lDfH8QKBgFWLYwrvW07Ck0DZHqEC+l+7RWXW9Id6ehTeg+7OyKwcjrrifzWsBUrQ
qiscUutyvOFTiYf+0S5i8Hj8PbjcJhGNLlEK6bi3sJQtusxKQkXuLtR+s2Rnhl8V
qE6oVfQtBUZbO9PQBrljcepuN/Ysm8L7njK1k6qnEXAnU/ITNsKK
-----END RSA PRIVATE KEY-----"""

RSA_PUBLIC = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAoVNhyYkByaNZdOQGVR58
tRKdbpO4vEzUaqm2P7lhARJccr1mbCDxw7iIt69jIl/88hviJnWf5W+LuPDr6egp
N7WPuZb1lvhVK+sie4P3NpsnBn8DG/By/sypBqe6yFB8i28OpF3636fhxHm6RbJS
NM4foDdlPXgnAAyrm2Z7QPBTfLqmLemcmvPsO0B5LRNORvxzoHlKqgAUgd2siR5a
SSRp5gmxRXGwfwMyaUsPajLuRaE5c9ddySwjbXLpqUUZggewaTkm16PQ2W3MqPtQ
aKSDdAbDDoB/b+UbaBlUeqT2U3fTrRQRMua1rKx/ueLx5ZNaKVfdOqprJe80Q+Vf
vwIDAQAB
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
