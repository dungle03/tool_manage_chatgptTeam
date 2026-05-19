from datetime import datetime

from app.models import PersonalAccount

TOKEN_PREVIEW_LENGTH = 6


def personal_account_to_public(account: PersonalAccount) -> dict:
    """Return a frontend-safe personal account shape without raw token values."""
    return {
        "id": account.id,
        "provider": account.provider,
        "auth_type": account.auth_type,
        "email": account.email,
        "name": account.name,
        "plan_type": account.plan_type,
        "status": account.status,
        "is_active": account.is_active,
        "token_expires_at": account.token_expires_at,
        "last_checked_at": account.last_checked_at,
        "last_refreshed_at": account.last_refreshed_at,
        "next_refresh_at": account.next_refresh_at,
        "last_error_code": account.last_error_code,
        "last_error_message": account.last_error_message,
        "oauth_connected": bool(account.refresh_token),
        "requires_relogin": account.status == "need_relogin",
        "created_at": account.created_at,
        "updated_at": account.updated_at,
    }


def mask_token(token: str | None) -> str | None:
    """Return a non-sensitive token preview for internal diagnostics."""
    if not token:
        return None
    if len(token) <= TOKEN_PREVIEW_LENGTH * 2:
        return "***"
    return f"{token[:TOKEN_PREVIEW_LENGTH]}...{token[-TOKEN_PREVIEW_LENGTH:]}"


def token_metadata(account: PersonalAccount) -> dict[str, str | datetime | None | bool]:
    """Return safe token metadata without raw token values."""
    return {
        "has_access_token": bool(account.access_token),
        "has_refresh_token": bool(account.refresh_token),
        "has_id_token": bool(account.id_token),
        "access_token_preview": mask_token(account.access_token),
        "refresh_token_preview": mask_token(account.refresh_token),
        "id_token_preview": mask_token(account.id_token),
        "token_expires_at": account.token_expires_at,
        "refresh_token_updated_at": account.refresh_token_updated_at,
    }
