"""
Integration tests — KAN-67: Docker Dev Env health checks.

Tests the /health endpoint under healthy, degraded-DB, and degraded-Redis conditions
by mocking AsyncSessionLocal and ping_redis at the module level.
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ── Helpers ──────────────────────────────────────────────────────────────────


class _HealthySessionCM:
    """Async context manager that simulates a responsive Postgres session."""

    async def __aenter__(self):
        session = AsyncMock()
        session.execute = AsyncMock()
        return session

    async def __aexit__(self, *args):
        return False


class _BrokenSessionCM:
    """Async context manager that raises on __aenter__ (DB unreachable)."""

    async def __aenter__(self):
        raise OSError("Connection refused")

    async def __aexit__(self, *args):
        return False


# ── Tests ────────────────────────────────────────────────────────────────────


class TestHealthEndpoint:
    """KAN-67 Gate: GET /health → 200 with structured status payload."""

    async def test_health_returns_200_always(self, async_client):
        """Health endpoint must always return HTTP 200 (never 503/500)."""
        with (
            patch("app.core.database.AsyncSessionLocal", return_value=_BrokenSessionCM()),
            patch("app.main.ping_redis", new=AsyncMock(return_value=False)),
        ):
            resp = await async_client.get("/health")
        assert resp.status_code == 200

    async def test_health_all_services_up(self, async_client):
        """With healthy DB and Redis → status='healthy'."""
        with (
            patch("app.core.database.AsyncSessionLocal", return_value=_HealthySessionCM()),
            patch("app.main.ping_redis", new=AsyncMock(return_value=True)),
        ):
            resp = await async_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "healthy"
        assert data["db"] == "connected"
        assert data["redis"] == "connected"

    async def test_health_db_down(self, async_client):
        """With unreachable Postgres → status='degraded', db='disconnected'."""
        with (
            patch("app.core.database.AsyncSessionLocal", return_value=_BrokenSessionCM()),
            patch("app.main.ping_redis", new=AsyncMock(return_value=True)),
        ):
            resp = await async_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["db"] == "disconnected"
        assert data["redis"] == "connected"

    async def test_health_redis_down(self, async_client):
        """With unreachable Redis → status='degraded', redis='disconnected'."""
        with (
            patch("app.core.database.AsyncSessionLocal", return_value=_HealthySessionCM()),
            patch("app.main.ping_redis", new=AsyncMock(return_value=False)),
        ):
            resp = await async_client.get("/health")

        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "degraded"
        assert data["db"] == "connected"
        assert data["redis"] == "disconnected"

    async def test_health_response_has_required_keys(self, async_client):
        """Response must include status, db, redis, env keys."""
        with (
            patch("app.core.database.AsyncSessionLocal", return_value=_BrokenSessionCM()),
            patch("app.main.ping_redis", new=AsyncMock(return_value=False)),
        ):
            resp = await async_client.get("/health")

        data = resp.json()
        assert {"status", "db", "redis", "env"}.issubset(data.keys())

    async def test_health_both_services_down(self, async_client):
        """Both DB and Redis down → status='degraded'."""
        with (
            patch("app.core.database.AsyncSessionLocal", return_value=_BrokenSessionCM()),
            patch("app.main.ping_redis", new=AsyncMock(return_value=False)),
        ):
            resp = await async_client.get("/health")

        data = resp.json()
        assert data["status"] == "degraded"
        assert data["db"] == "disconnected"
        assert data["redis"] == "disconnected"
