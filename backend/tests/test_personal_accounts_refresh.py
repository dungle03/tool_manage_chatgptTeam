import asyncio
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest
from fastapi import HTTPException

from app.db import SessionLocal
from app.models import PersonalAccount
from app.services.personal_accounts import refresh


def _jwt(email: str = "user@example.com", sub: str = "acct_1") -> str:
    return jwt.encode(
        {
            "email": email,
            "sub": sub,
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        "test-secret",
        algorithm="HS256",
    )


@pytest.fixture(autouse=True)
def _clear_refresh_state(monkeypatch):
    refresh._REFRESH_LOCKS.clear()
    refresh._REFRESH_TASKS.clear()
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_CHATGPT_OAUTH", "true")
    yield
    refresh._REFRESH_LOCKS.clear()
    refresh._REFRESH_TASKS.clear()


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def _account(db_session, **overrides):
    account = PersonalAccount(
        provider="codex",
        provider_account_id=overrides.pop("provider_account_id", "acct_1"),
        email=overrides.pop("email", "user@example.com"),
        name=overrides.pop("name", "User"),
        status=overrides.pop("status", "live"),
        auth_type="oauth",
        access_token=overrides.pop("access_token", _jwt()),
        refresh_token=overrides.pop("refresh_token", "old-refresh"),
        is_active=True,
        **overrides,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def test_refresh_success_updates_rotated_tokens(client, db_session, monkeypatch):
    account = _account(db_session)
    new_access = _jwt()
    monkeypatch.setattr(
        refresh,
        "exchange_refresh_token",
        AsyncMock(
            return_value={
                "access_token": new_access,
                "refresh_token": "new-refresh",
                "id_token": "new-id-token",
                "expires_in": 3600,
            }
        ),
    )

    response = client.post(f"/api/personal-accounts/{account.id}/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["account"]["status"] == "live"
    assert data["account"]["oauth_connected"] is True
    assert "access_token" not in str(data)
    db_session.refresh(account)
    assert account.access_token == new_access
    assert account.refresh_token == "new-refresh"
    assert account.id_token == "new-id-token"
    assert account.last_refreshed_at is not None
    assert account.next_refresh_at is not None


def test_refresh_missing_refresh_token_marks_need_relogin(client, db_session):
    account = _account(db_session, refresh_token=None)

    response = client.post(f"/api/personal-accounts/{account.id}/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["account"]["status"] == "need_relogin"
    assert data["account"]["requires_relogin"] is True
    assert data["next_action"] == "reconnect"
    db_session.refresh(account)
    assert account.last_error_code == "missing_refresh_token"


def test_invalid_grant_marks_need_relogin_without_retry(
    client, db_session, monkeypatch
):
    account = _account(db_session)
    exchange = AsyncMock(
        side_effect=HTTPException(
            status_code=400,
            detail={"code": "invalid_grant", "message": "expired refresh token"},
        )
    )
    monkeypatch.setattr(refresh, "exchange_refresh_token", exchange)

    response = client.post(f"/api/personal-accounts/{account.id}/refresh")

    assert response.status_code == 200
    assert response.json()["account"]["status"] == "need_relogin"
    assert response.json()["next_action"] == "reconnect"
    assert exchange.await_count == 1
    db_session.refresh(account)
    assert account.last_error_code == "invalid_grant"
    assert account.refresh_token == "old-refresh"


def test_health_check_marks_live(client, db_session, monkeypatch):
    account = _account(db_session, status="die")
    monkeypatch.setattr(
        "app.services.personal_accounts.health.chatgpt_service.get_account_info",
        AsyncMock(return_value=[]),
    )

    response = client.post(f"/api/personal-accounts/{account.id}/check")

    assert response.status_code == 200
    assert response.json()["account"]["status"] == "live"
    db_session.refresh(account)
    assert account.last_checked_at is not None
    assert account.last_error_code is None


@pytest.mark.anyio
async def test_parallel_refresh_reuses_active_task(db_session, monkeypatch):
    account = _account(db_session)
    calls = 0

    async def fake_exchange(_refresh_token):
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return {
            "access_token": _jwt(),
            "refresh_token": "rotated-refresh",
            "expires_in": 3600,
        }

    monkeypatch.setattr(refresh, "exchange_refresh_token", fake_exchange)

    result1, result2 = await asyncio.gather(
        refresh.refresh_personal_account(db_session, account),
        refresh.refresh_personal_account(db_session, account),
    )

    assert calls == 1
    assert result1["id"] == account.id
    assert result2["id"] == account.id
    db_session.refresh(account)
    assert account.refresh_token == "rotated-refresh"
