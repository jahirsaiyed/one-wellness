"""
FastAPI dependency injection — auth, RBAC, DB session.
KAN-19 subtask KAN-76: RBAC FastAPI Depends guards for all 4 roles.
"""
from __future__ import annotations

import uuid
from typing import Annotated

import structlog
from fastapi import Cookie, Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.redis import get_redis
from app.core.security import decode_token
from app.models.user import User, UserRole

logger = structlog.get_logger()

_bearer = HTTPBearer(auto_error=False)

# ── Token extraction ─────────────────────────────────────────────────────────


def _extract_token(
    credentials: HTTPAuthorizationCredentials | None,
    access_token_cookie: str | None,
) -> str | None:
    if credentials:
        return credentials.credentials
    return access_token_cookie


# ── Core auth dependency ─────────────────────────────────────────────────────


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    token = _extract_token(credentials, access_token)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(token)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Wrong token type",
        )

    # Check blacklist
    jti = payload.get("jti")
    if jti and await redis.get(f"blacklisted:{jti}"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has been revoked",
        )

    user_id = payload.get("sub")
    try:
        uid = uuid.UUID(user_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Bad token subject")

    result = await db.execute(select(User).where(User.id == uid, User.deleted_at.is_(None)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or deactivated",
        )

    return user


async def get_current_active_user(
    user: Annotated[User, Depends(get_current_user)],
) -> User:
    if not user.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account deactivated")
    return user


# ── TOTP-aware dependency ─────────────────────────────────────────────────────


async def get_totp_verified_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    access_token: Annotated[str | None, Cookie()] = None,
    db: AsyncSession = Depends(get_db),
    redis=Depends(get_redis),
) -> User:
    """For therapist/admin routes: requires totp_verified=True in token."""
    user = await get_current_user(credentials, access_token, db, redis)

    if user.requires_totp:
        token = _extract_token(credentials, access_token)
        payload = decode_token(token)  # already validated above
        if not payload.get("totp_verified"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="TOTP verification required",
            )
    return user


# ── Role guards ───────────────────────────────────────────────────────────────


def require_roles(*roles: UserRole):
    """Factory returning a dependency that enforces one of the given roles."""

    async def _guard(user: Annotated[User, Depends(get_totp_verified_user)]) -> User:
        if user.role not in {r.value for r in roles}:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Requires role: {', '.join(r.value for r in roles)}",
            )
        return user

    return _guard


# ── Convenience aliases ───────────────────────────────────────────────────────

RequireClient = Depends(require_roles(UserRole.client))
RequireTherapist = Depends(require_roles(UserRole.therapist))
RequireAdmin = Depends(require_roles(UserRole.platform_admin))
RequireHRAdmin = Depends(require_roles(UserRole.hr_admin))
RequireAnyStaff = Depends(
    require_roles(UserRole.therapist, UserRole.hr_admin, UserRole.platform_admin)
)
