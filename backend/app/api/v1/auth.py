"""
Auth router — KAN-19 (Register/Login/Refresh/Google), KAN-20 (TOTP), KAN-21 (Delete request).
Subtasks: KAN-72..76, KAN-81..83, KAN-88.
"""
from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Annotated

import structlog
from fastapi import APIRouter, BackgroundTasks, Cookie, Depends, HTTPException, Request, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_current_active_user
from app.core.config import settings
from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import (
    build_google_auth_url,
    create_access_token,
    create_refresh_token,
    decode_token,
    exchange_google_code,
    generate_backup_codes,
    generate_totp_secret,
    get_totp_uri,
    hash_password,
    verify_backup_code,
    verify_password,
    verify_totp_code,
)
from app.models.user import User, UserRole
from app.schemas.auth import (
    DeleteRequestResponse,
    GoogleCallbackResponse,
    LoginRequest,
    RefreshRequest,
    RefreshResponse,
    RegisterRequest,
    TOTPSetupResponse,
    TOTPVerifyRequest,
    TOTPVerifyResponse,
    TokenResponse,
)

logger = structlog.get_logger()
router = APIRouter(prefix="/auth", tags=["auth"])

_REFRESH_TTL = settings.REFRESH_TOKEN_EXPIRE_DAYS * 86_400  # seconds


# ── Helpers ───────────────────────────────────────────────────────────────────


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    secure = settings.APP_ENV != "development"
    response.set_cookie("access_token", access_token, httponly=True, secure=secure, samesite="lax", max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    response.set_cookie("refresh_token", refresh_token, httponly=True, secure=secure, samesite="lax", max_age=_REFRESH_TTL, path="/v1/auth/token")


async def _store_refresh_token(redis, jti: str, user_id: str) -> None:
    await redis.setex(f"refresh_token:{jti}", _REFRESH_TTL, user_id)


async def _revoke_refresh_token(redis, jti: str) -> None:
    await redis.delete(f"refresh_token:{jti}")


def _issue_tokens(user: User, totp_verified: bool = False) -> tuple[str, str, str, str]:
    """Return (access_token, access_jti, refresh_token, refresh_jti)."""
    access_token, access_jti = create_access_token(
        subject=str(user.id), role=user.role, totp_verified=totp_verified
    )
    refresh_token, refresh_jti = create_refresh_token(subject=str(user.id))
    return access_token, access_jti, refresh_token, refresh_jti


# ── POST /register (KAN-72) ───────────────────────────────────────────────────


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=TokenResponse)
async def register(
    body: RegisterRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=UserRole.client.value,
        preferred_language=body.preferred_language,
        timezone=body.timezone,
    )
    db.add(user)
    await db.flush()  # get user.id before commit

    access_token, _, refresh_token, refresh_jti = _issue_tokens(user)
    await _store_refresh_token(redis, refresh_jti, str(user.id))
    _set_auth_cookies(response, access_token, refresh_token)

    logger.info("user.registered", user_id=str(user.id), role=user.role)
    return TokenResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        requires_totp=False,
    )


# ── POST /login (KAN-73) ──────────────────────────────────────────────────────


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TokenResponse:
    result = await db.execute(
        select(User).where(User.email == body.email.lower(), User.deleted_at.is_(None))
    )
    user = result.scalar_one_or_none()

    if not user or not user.hashed_password or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    totp_verified = not user.requires_totp or not user.totp_confirmed
    access_token, _, refresh_token, refresh_jti = _issue_tokens(user, totp_verified=totp_verified)
    await _store_refresh_token(redis, refresh_jti, str(user.id))
    _set_auth_cookies(response, access_token, refresh_token)

    requires_totp = user.requires_totp and user.totp_confirmed
    logger.info("user.login", user_id=str(user.id), requires_totp=requires_totp)

    return TokenResponse(
        user_id=user.id,
        email=user.email,
        role=user.role,
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        requires_totp=requires_totp,
    )


# ── POST /token/refresh (KAN-75) ──────────────────────────────────────────────


@router.post("/token/refresh", response_model=RefreshResponse)
async def refresh_token(
    response: Response,
    body: RefreshRequest | None = None,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> RefreshResponse:
    token_str = (body.refresh_token if body else None) or refresh_token_cookie
    if not token_str:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token missing")

    try:
        payload = decode_token(token_str)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Wrong token type")

    jti = payload["jti"]
    stored = await redis.get(f"refresh_token:{jti}")
    if not stored:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token expired or revoked")

    user_id = payload["sub"]
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id), User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    # Rotate: revoke old, issue new
    await _revoke_refresh_token(redis, jti)
    totp_verified = not user.requires_totp or not user.totp_confirmed
    new_access, _, new_refresh, new_refresh_jti = _issue_tokens(user, totp_verified=totp_verified)
    await _store_refresh_token(redis, new_refresh_jti, str(user.id))
    _set_auth_cookies(response, new_access, new_refresh)

    return RefreshResponse(
        access_token=new_access,
        refresh_token=new_refresh,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


# ── POST /logout ──────────────────────────────────────────────────────────────


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    response: Response,
    refresh_token_cookie: Annotated[str | None, Cookie(alias="refresh_token")] = None,
    user: User = Depends(get_current_user),
    redis=Depends(get_redis),
) -> None:
    if refresh_token_cookie:
        try:
            payload = decode_token(refresh_token_cookie)
            await _revoke_refresh_token(redis, payload["jti"])
        except (ValueError, KeyError):
            pass

    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token", path="/v1/auth/token")
    logger.info("user.logout", user_id=str(user.id))


# ── GET /google/authorize (KAN-74) ────────────────────────────────────────────


@router.get("/google/authorize")
async def google_authorize(state: str) -> RedirectResponse:
    url = build_google_auth_url(state)
    return RedirectResponse(url, status_code=302)


# ── GET /google/callback (KAN-74) ─────────────────────────────────────────────


@router.get("/google/callback", response_model=GoogleCallbackResponse)
async def google_callback(
    code: str,
    state: str,
    response: Response,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> GoogleCallbackResponse:
    try:
        info = await exchange_google_code(code)
    except Exception as exc:
        logger.warning("google.oauth.failed", error=str(exc))
        raise HTTPException(status_code=400, detail="Google OAuth failed")

    google_sub = info.get("sub")
    email = info.get("email", "").lower()
    full_name = info.get("name", email.split("@")[0])

    if not google_sub or not email:
        raise HTTPException(status_code=400, detail="Insufficient Google profile data")

    result = await db.execute(select(User).where(User.google_sub == google_sub))
    user = result.scalar_one_or_none()
    is_new_user = user is None

    if is_new_user:
        # Also check by email in case they previously registered with password
        result = await db.execute(select(User).where(User.email == email, User.deleted_at.is_(None)))
        user = result.scalar_one_or_none()
        if user:
            user.google_sub = google_sub  # link accounts
        else:
            user = User(
                email=email,
                full_name=full_name,
                google_sub=google_sub,
                role=UserRole.client.value,
            )
            db.add(user)
            await db.flush()

    access_token, _, refresh_token, refresh_jti = _issue_tokens(user)
    await _store_refresh_token(redis, refresh_jti, str(user.id))
    _set_auth_cookies(response, access_token, refresh_token)

    logger.info("user.google_login", user_id=str(user.id), is_new=is_new_user)
    return GoogleCallbackResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        is_new_user=is_new_user,
    )


# ── POST /totp/setup (KAN-81) ─────────────────────────────────────────────────


@router.post("/totp/setup", response_model=TOTPSetupResponse)
async def totp_setup(
    user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> TOTPSetupResponse:
    secret = generate_totp_secret()
    qr_uri = get_totp_uri(secret, user.email)
    plain_codes, hashed_codes = generate_backup_codes()

    user.totp_secret = secret
    user.totp_backup_codes = hashed_codes
    user.totp_confirmed = False  # Must verify before confirmed

    logger.info("totp.setup", user_id=str(user.id))
    return TOTPSetupResponse(secret=secret, qr_uri=qr_uri, backup_codes=plain_codes)


# ── POST /totp/verify (KAN-82) ────────────────────────────────────────────────


@router.post("/totp/verify", response_model=TOTPVerifyResponse)
async def totp_verify(
    body: TOTPVerifyRequest,
    user: Annotated[User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> TOTPVerifyResponse:
    if not user.totp_secret:
        raise HTTPException(status_code=400, detail="TOTP not set up. Call /totp/setup first.")

    # Try TOTP code first
    valid = verify_totp_code(user.totp_secret, body.code)

    # Fall back to backup code
    if not valid and user.totp_backup_codes:
        idx = verify_backup_code(body.code, user.totp_backup_codes)
        if idx is not None:
            # Consume backup code (one-time use)
            codes = list(user.totp_backup_codes)
            codes.pop(idx)
            user.totp_backup_codes = codes
            valid = True

    if not valid:
        raise HTTPException(status_code=400, detail="Invalid TOTP code")

    user.totp_confirmed = True

    # Issue upgraded access token with totp_verified=True
    access_token, _ = create_access_token(subject=str(user.id), role=user.role, totp_verified=True)
    logger.info("totp.verified", user_id=str(user.id))
    return TOTPVerifyResponse(verified=True, access_token=access_token)
