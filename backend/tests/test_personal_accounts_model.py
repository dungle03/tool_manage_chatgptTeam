from datetime import datetime, timedelta, timezone

from app.db import SessionLocal
from app.models import PersonalAccount
from app.services.personal_accounts.serializers import (
    personal_account_to_public,
    token_metadata,
)


def test_personal_account_model_fields_exist():
    assert hasattr(PersonalAccount, "provider")
    assert hasattr(PersonalAccount, "provider_account_id")
    assert hasattr(PersonalAccount, "email")
    assert hasattr(PersonalAccount, "access_token")
    assert hasattr(PersonalAccount, "refresh_token")
    assert hasattr(PersonalAccount, "id_token")
    assert hasattr(PersonalAccount, "token_expires_at")
    assert hasattr(PersonalAccount, "reauth_required_at")


def test_personal_account_can_be_inserted_and_read_back():
    session = SessionLocal()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=1)
    try:
        account = PersonalAccount(
            provider="codex",
            provider_account_id="user_123",
            email="personal@example.com",
            name="Personal User",
            plan_type="plus",
            status="live",
            access_token="access-secret",
            refresh_token="refresh-secret",
            id_token="id-secret",
            token_expires_at=expires_at,
        )
        session.add(account)
        session.commit()

        saved = (
            session.query(PersonalAccount)
            .filter(
                PersonalAccount.provider == "codex",
                PersonalAccount.email == "personal@example.com",
            )
            .one()
        )

        assert saved.provider_account_id == "user_123"
        assert saved.plan_type == "plus"
        assert saved.status == "live"
        assert saved.access_token == "access-secret"
        assert saved.refresh_token == "refresh-secret"
        assert saved.id_token == "id-secret"
    finally:
        session.close()


def test_personal_account_public_serializer_excludes_tokens():
    account = PersonalAccount(
        id=1,
        provider="codex",
        email="personal@example.com",
        name="Personal User",
        plan_type="pro",
        status="need_relogin",
        access_token="access-secret",
        refresh_token="refresh-secret",
        id_token="id-secret",
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )

    public = personal_account_to_public(account)

    assert public["email"] == "personal@example.com"
    assert public["oauth_connected"] is True
    assert public["requires_relogin"] is True
    assert "access_token" not in public
    assert "refresh_token" not in public
    assert "id_token" not in public


def test_personal_account_duplicate_email_can_be_detected():
    session = SessionLocal()
    try:
        session.add(
            PersonalAccount(
                provider="codex",
                provider_account_id="user_existing",
                email="duplicate@example.com",
                name="Existing User",
            )
        )
        session.commit()

        duplicate = (
            session.query(PersonalAccount)
            .filter(
                PersonalAccount.provider == "codex",
                PersonalAccount.email == "duplicate@example.com",
            )
            .first()
        )

        assert duplicate is not None
        assert duplicate.provider_account_id == "user_existing"
    finally:
        session.close()


def test_token_metadata_masks_token_values():
    account = PersonalAccount(
        email="personal@example.com",
        access_token="access-token-secret-value",
        refresh_token="refresh-token-secret-value",
        id_token="id-token-secret-value",
    )

    metadata = token_metadata(account)

    assert metadata["has_access_token"] is True
    assert metadata["has_refresh_token"] is True
    assert metadata["has_id_token"] is True
    assert metadata["access_token_preview"] == "access...-value"
    assert metadata["refresh_token_preview"] == "refres...-value"
    assert metadata["id_token_preview"] == "id-tok...-value"
    assert "access-token-secret-value" not in metadata.values()
    assert "refresh-token-secret-value" not in metadata.values()
    assert "id-token-secret-value" not in metadata.values()
