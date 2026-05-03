"""
Security utilities — JWT RS256, password hashing, TOTP, Google OAuth2.
KAN-19 (Auth), KAN-20 (2FA)
"""
from __future__ import annotations

import secrets
import uuid
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlencode

import httpx
import pyotp
from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "RS256"
TOTP_ISSUER = "GCCWellness"
BACKUP_CODE_COUNT = 8


# ── Key loading ──────────────────────────────────────────────────────────────

def _load_private_key() -> str:
    if settings.JWT_PRIVATE_KEY_FILE:
        return Path(settings.JWT_PRIVATE_KEY_FILE).read_text()
    return settings.JWT_PRIVATE_KEY


def _load_public_key() -> str:
    return settings.JWT_PUBLIC_KEY


# ── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(
    subject: str,
    role: str,
    totp_verified: bool = False,
    extra_claims: dict | None = None,
) -> tuple[str, str]:
    """Return (token, jti)."""
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {
        "sub": subject,
        "jti": jti,
        "role": role,
        "totp_verified": totp_verified,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "access",
        **(extra_claims or {}),
    }
    token = jwt.encode(payload, _load_private_key(), algorithm=ALGORITHM)
    return token, jti


def create_refresh_token(subject: str) -> tuple[str, str]:
    """Return (token, jti)."""
    jti = str(uuid.uuid4())
    expire = datetime.now(UTC) + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    payload = {
        "sub": subject,
        "jti": jti,
        "exp": expire,
        "iat": datetime.now(UTC),
        "type": "refresh",
    }
    token = jwt.encode(payload, _load_private_key(), algorithm=ALGORITHM)
    return token, jti


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, _load_public_key(), algorithms=[ALGORITHM])
    except JWTError as exc:
        raise ValueError("Invalid or expired token") from exc


# ── Password ─────────────────────────────────────────────────────────────────

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ── TOTP (KAN-20) ────────────────────────────────────────────────────────────

def generate_totp_secret() -> str:
    return pyotp.random_base32()


def get_totp_uri(secret: str, email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=email, issuer_name=TOTP_ISSUER
    )


def verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.TOTP(secret)
    # Allow 1 window of drift (30s) in each direction
    return totp.verify(code, valid_window=1)


def generate_backup_codes() -> tuple[list[str], list[str]]:
    """Return (plaintext_codes, hashed_codes) for TOTP backup."""
    plain: list[str] = []
    hashed: list[str] = []
    for _ in range(BACKUP_CODE_COUNT):
        code = secrets.token_hex(4).upper()  # e.g. "A3F2B1C0"
        plain.append(f"{code[:4]}-{code[4:]}")
        hashed.append(pwd_context.hash(code))
    return plain, hashed


def verify_backup_code(code: str, hashed_codes: list[str]) -> int | None:
    """Return index of matched code or None. Caller must remove used code."""
    normalized = code.replace("-", "").upper()
    for i, h in enumerate(hashed_codes):
        if pwd_context.verify(normalized, h):
            return i
    return None


# ── Google OAuth2 ────────────────────────────────────────────────────────────

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"
GOOGLE_SCOPES = "openid email profile"


def build_google_auth_url(state: str) -> str:
    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": settings.GOOGLE_REDIRECT_URI,
        "response_type": "code",
        "scope": GOOGLE_SCOPES,
        "state": state,
        "access_type": "offline",
        "prompt": "select_account",
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_google_code(code: str) -> dict:
    """Exchange authorization code for Google user info."""
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": settings.GOOGLE_REDIRECT_URI,
                "grant_type": "authorization_code",
            },
        )
        token_resp.raise_for_status()
        access_token = token_resp.json()["access_token"]

        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        userinfo_resp.raise_for_status()
        return userinfo_resp.json()
