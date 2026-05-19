from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest

from app.db import SessionLocal
from app.models import PersonalAccount
from app.services.personal_accounts import oauth, refresh


def _jwt(email: str = "api@example.com", sub: str = "acct_api") -> str:
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
def _clear_state(monkeypatch):
    oauth._pending_oauth_states.clear()
    oauth._pending_duplicates.clear()
    refresh._REFRESH_LOCKS.clear()
    refresh._REFRESH_TASKS.clear()
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_CHATGPT_OAUTH", "true")
    yield
    oauth._pending_oauth_states.clear()
    oauth._pending_duplicates.clear()
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
        provider_account_id=overrides.pop("provider_account_id", "acct_api"),
        email=overrides.pop("email", "api@example.com"),
        name=overrides.pop("name", "API User"),
        plan_type=overrides.pop("plan_type", "plus"),
        status=overrides.pop("status", "live"),
        auth_type="oauth",
        access_token=overrides.pop("access_token", _jwt()),
        refresh_token=overrides.pop("refresh_token", "refresh-secret"),
        id_token=overrides.pop("id_token", "id-secret"),
        is_active=overrides.pop("is_active", True),
        **overrides,
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)
    return account


def _assert_no_tokens(payload):
    text = str(payload)
    assert "access_token" not in text
    assert "refresh_token" not in text
    assert "id_token" not in text
    assert "refresh-secret" not in text
    assert "id-secret" not in text


def test_list_and_detail_return_public_shape(client, db_session):
    account = _account(db_session)
    _account(db_session, email="deleted@example.com", is_active=False)

    listed = client.get("/api/personal-accounts")
    detail = client.get(f"/api/personal-accounts/{account.id}")

    assert listed.status_code == 200
    assert len(listed.json()) == 1
    assert listed.json()[0]["email"] == "api@example.com"
    assert detail.status_code == 200
    assert detail.json()["id"] == account.id
    _assert_no_tokens(listed.json())
    _assert_no_tokens(detail.json())


def test_delete_soft_deactivates_account(client, db_session):
    account = _account(db_session)

    response = client.delete(f"/api/personal-accounts/{account.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["account"]["status"] == "deleted"
    db_session.refresh(account)
    assert account.is_active is False
    assert client.get(f"/api/personal-accounts/{account.id}").status_code == 404


def test_refresh_endpoint_returns_action_result(client, db_session, monkeypatch):
    account = _account(db_session)
    monkeypatch.setattr(
        refresh,
        "exchange_refresh_token",
        AsyncMock(
            return_value={
                "access_token": _jwt(),
                "refresh_token": "rotated-refresh",
                "expires_in": 3600,
            }
        ),
    )

    response = client.post(f"/api/personal-accounts/{account.id}/refresh")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["message"] == "Account refreshed"
    assert data["account"]["status"] == "live"
    assert data["next_action"] is None
    _assert_no_tokens(data)


def test_check_endpoint_returns_reconnect_next_action(client, db_session, monkeypatch):
    account = _account(db_session)
    monkeypatch.setattr(
        "app.services.personal_accounts.health.chatgpt_service.get_account_info",
        AsyncMock(side_effect=RuntimeError("expired")),
    )

    response = client.post(f"/api/personal-accounts/{account.id}/check")

    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["message"] == "Account checked"
    assert data["account"]["status"] == "die"
    assert data["next_action"] is None
    _assert_no_tokens(data)


def test_reconnect_start_returns_oauth_url(client, db_session):
    account = _account(db_session)

    response = client.post(f"/api/personal-accounts/{account.id}/reconnect/start")

    assert response.status_code == 200
    assert response.json()["authorization_url"].startswith(
        "https://auth.openai.com/oauth/authorize?"
    )


def test_duplicate_callback_response_supports_ui_modal(client, db_session, monkeypatch):
    existing = _account(db_session, email="dupe-api@example.com")
    start = client.post("/api/personal-accounts/oauth/start").json()
    monkeypatch.setattr(
        oauth,
        "exchange_authorization_code",
        AsyncMock(
            return_value={
                "access_token": _jwt(email="dupe-api@example.com", sub="new-sub"),
                "refresh_token": "new-refresh-secret",
                "id_token": _jwt(email="dupe-api@example.com", sub="new-sub"),
            }
        ),
    )

    response = client.get(
        "/api/personal-accounts/oauth/callback",
        params={"code": "code", "state": start["state"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "duplicate_detected"
    assert data["duplicate_token"]
    assert data["existing_account"]["id"] == existing.id
    assert data["new_account"]["email"] == "dupe-api@example.com"
    _assert_no_tokens(data)
