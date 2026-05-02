"""
JWT skeleton — RS256 signing/verification.
Full implementation is Sprint 1 KAN-19.
"""
from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "RS256"


def _load_private_key() -> str:
    if settings.JWT_PRIVATE_KEY_FILE:
        return Path(settings.JWT_PRIVATE_KEY_FILE).read_text()
    return settings.JWT_PRIVATE_KEY


def _load_public_key() -> str:
    return settings.JWT_PUBLIC_KEY


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        **(extra_claims or {}),
    }
    return jwt.encode(payload, _load_private_key(), algorithm=ALGORITHM)


def create_refresh_token(subject: str) -> str:
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    return jwt.encode(payload, _load_private_key(), algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _load_public_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)
