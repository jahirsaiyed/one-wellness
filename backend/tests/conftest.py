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


# ── RSA test keys (shared across all tests) ───────────────────────────────────

RSA_TEST_PRIVATE_KEY = """-----BEGIN RSA PRIVATE KEY-----
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

RSA_TEST_PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAoVNhyYkByaNZdOQGVR58
tRKdbpO4vEzUaqm2P7lhARJccr1mbCDxw7iIt69jIl/88hviJnWf5W+LuPDr6egp
N7WPuZb1lvhVK+sie4P3NpsnBn8DG/By/sypBqe6yFB8i28OpF3636fhxHm6RbJS
NM4foDdlPXgnAAyrm2Z7QPBTfLqmLemcmvPsO0B5LRNORvxzoHlKqgAUgd2siR5a
SSRp5gmxRXGwfwMyaUsPajLuRaE5c9ddySwjbXLpqUUZggewaTkm16PQ2W3MqPtQ
aKSDdAbDDoB/b+UbaBlUeqT2U3fTrRQRMua1rKx/ueLx5ZNaKVfdOqprJe80Q+Vf
vwIDAQAB
-----END PUBLIC KEY-----"""


@pytest.fixture(autouse=True)
def patch_jwt_keys(monkeypatch):
    """Patch RS256 keys for all tests. test_auth.py's own patch_keys is a harmless duplicate."""
    monkeypatch.setattr("app.core.security._load_private_key", lambda: RSA_TEST_PRIVATE_KEY)
    monkeypatch.setattr("app.core.security._load_public_key", lambda: RSA_TEST_PUBLIC_KEY)
