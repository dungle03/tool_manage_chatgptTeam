from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import jwt
import pytest

from app.db import SessionLocal
from app.models import PersonalAccount
from app.services.personal_accounts import oauth
from app.services.personal_accounts.oauth import create_pkce_pair


def _jwt(claims: dict) -> str:
    payload = {"exp": datetime.now(timezone.utc) + timedelta(hours=1), **claims}
    return jwt.encode(payload, "test-secret", algorithm="HS256")


@pytest.fixture
def db_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture(autouse=True)
def _clear_oauth_state(monkeypatch):
    oauth._pending_oauth_states.clear()
    oauth._pending_duplicates.clear()
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_CHATGPT_OAUTH", "true")
    yield
    oauth._pending_oauth_states.clear()
    oauth._pending_duplicates.clear()


def test_pkce_pair_is_urlsafe_and_sha256_based():
    verifier, challenge = create_pkce_pair()

    assert len(verifier) >= 43
    assert len(challenge) >= 43
    assert "=" not in challenge


def test_oauth_start_returns_authorization_url(client):
    response = client.post("/api/personal-accounts/oauth/start")

    assert response.status_code == 200
    data = response.json()
    assert data["authorization_url"].startswith(
        "https://auth.openai.com/oauth/authorize?"
    )
    assert "code_challenge=" in data["authorization_url"]
    assert data["state"]
    assert data["expires_in"] == 600


def test_oauth_start_can_be_disabled(client, monkeypatch):
    monkeypatch.setenv("ENABLE_EXPERIMENTAL_CHATGPT_OAUTH", "false")

    response = client.post("/api/personal-accounts/oauth/start")

    assert response.status_code == 403
    assert "disabled" in response.json()["detail"]


def test_callback_rejects_unknown_state(client):
    response = client.get(
        "/api/personal-accounts/oauth/callback",
        params={"code": "code", "state": "missing"},
    )

    assert response.status_code == 400
    assert "state" in response.json()["detail"].lower()


def test_callback_exchanges_code_and_stores_account(client, db_session, monkeypatch):
    start = client.post("/api/personal-accounts/oauth/start").json()
    token_response = {
        "access_token": _jwt({"email": "plus@example.com", "sub": "acct_1"}),
        "refresh_token": "refresh-token-secret",
        "id_token": _jwt(
            {"email": "plus@example.com", "sub": "acct_1", "name": "Plus User"}
        ),
        "expires_in": 3600,
    }
    monkeypatch.setattr(
        oauth,
        "exchange_authorization_code",
        AsyncMock(return_value=token_response),
    )

    response = client.get(
        "/api/personal-accounts/oauth/callback",
        params={"code": "code", "state": start["state"]},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["account"]["email"] == "plus@example.com"
    assert "access_token" not in data["account"]
    assert "refresh_token" not in data["account"]

    account = (
        db_session.query(PersonalAccount).filter_by(email="plus@example.com").one()
    )
    assert account.access_token == token_response["access_token"]
    assert account.refresh_token == "refresh-token-secret"
    assert account.status == "live"


def test_callback_detects_duplicate_and_resolution_overwrites(
    client, db_session, monkeypatch
):
    existing = PersonalAccount(
        provider="codex",
        provider_account_id="old-id",
        email="dupe@example.com",
        name="Old User",
        plan_type="plus",
        status="live",
        auth_type="oauth",
        access_token="old-access",
        refresh_token="old-refresh",
        id_token="old-id-token",
        is_active=True,
    )
    db_session.add(existing)
    db_session.commit()

    start = client.post("/api/personal-accounts/oauth/start").json()
    token_response = {
        "access_token": _jwt({"email": "dupe@example.com", "sub": "new-id"}),
        "refresh_token": "new-refresh",
        "id_token": _jwt(
            {"email": "dupe@example.com", "sub": "new-id", "name": "New User"}
        ),
        "expires_in": 3600,
    }
    monkeypatch.setattr(
        oauth,
        "exchange_authorization_code",
        AsyncMock(return_value=token_response),
    )

    response = client.get(
        "/api/personal-accounts/oauth/callback",
        params={"code": "code", "state": start["state"]},
    )

    assert response.status_code == 200
    duplicate = response.json()
    assert duplicate["status"] == "duplicate_detected"
    assert duplicate["duplicate_token"]
    assert duplicate["existing_account"]["email"] == "dupe@example.com"

    resolved = client.post(
        "/api/personal-accounts/oauth/resolve-duplicate",
        json={
            "duplicate_token": duplicate["duplicate_token"],
            "decision": "overwrite_existing",
        },
    )

    assert resolved.status_code == 200
    assert resolved.json()["status"] == "success"
    db_session.refresh(existing)
    assert existing.provider_account_id == "new-id"
    assert existing.refresh_token == "new-refresh"
    assert existing.name == "New User"


def test_duplicate_resolution_cancel_does_not_store_tokens(
    client, db_session, monkeypatch
):
    existing = PersonalAccount(
        provider="codex",
        provider_account_id="old-id",
        email="cancel@example.com",
        name="Old User",
        status="live",
        auth_type="oauth",
        access_token="old-access",
        refresh_token="old-refresh",
        is_active=True,
    )
    db_session.add(existing)
    db_session.commit()

    start = client.post("/api/personal-accounts/oauth/start").json()
    monkeypatch.setattr(
        oauth,
        "exchange_authorization_code",
        AsyncMock(
            return_value={
                "access_token": _jwt({"email": "cancel@example.com", "sub": "new-id"}),
                "refresh_token": "new-refresh",
                "id_token": _jwt({"email": "cancel@example.com", "sub": "new-id"}),
            }
        ),
    )
    duplicate = client.get(
        "/api/personal-accounts/oauth/callback",
        params={"code": "code", "state": start["state"]},
    ).json()

    resolved = client.post(
        "/api/personal-accounts/oauth/resolve-duplicate",
        json={"duplicate_token": duplicate["duplicate_token"], "decision": "cancel"},
    )

    assert resolved.status_code == 200
    assert resolved.json() == {
        "status": "cancelled",
        "account": None,
        "duplicate_token": None,
        "existing_account": None,
        "new_account": None,
    }
    assert (
        db_session.query(PersonalAccount).filter_by(email="cancel@example.com").count()
        == 1
    )
    db_session.refresh(existing)
    assert existing.refresh_token == "old-refresh"


def test_parse_oauth_callback_url_extracts_code_and_state():
    parsed = oauth.parse_oauth_callback_url(
        "http://localhost:1455/callback?code=abc123&state=state456&ignored=1"
    )

    assert parsed == {"code": "abc123", "state": "state456"}


def test_callback_url_endpoint_exchanges_code_and_stores_account(
    client, db_session, monkeypatch
):
    start = client.post("/api/personal-accounts/oauth/start").json()
    token_response = {
        "access_token": _jwt({"email": "callback-url@example.com", "sub": "acct_cb"}),
        "refresh_token": "callback-refresh-token",
        "id_token": _jwt(
            {
                "email": "callback-url@example.com",
                "sub": "acct_cb",
                "name": "Callback User",
            }
        ),
        "expires_in": 3600,
    }
    exchange = AsyncMock(return_value=token_response)
    monkeypatch.setattr(oauth, "exchange_authorization_code", exchange)

    response = client.post(
        "/api/personal-accounts/oauth/callback-url",
        json={
            "callback_url": (
                "http://localhost:8484/callback"
                f"?code=callback-code&state={start['state']}"
            )
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["account"]["email"] == "callback-url@example.com"
    exchange.assert_awaited_once()

    account = (
        db_session.query(PersonalAccount)
        .filter_by(email="callback-url@example.com")
        .one()
    )
    assert account.refresh_token == "callback-refresh-token"


def test_callback_url_endpoint_rejects_missing_code(client):
    response = client.post(
        "/api/personal-accounts/oauth/callback-url",
        json={"callback_url": "http://localhost:8484/callback?state=only-state"},
    )

    assert response.status_code == 400
    assert "code and state" in response.json()["detail"]
