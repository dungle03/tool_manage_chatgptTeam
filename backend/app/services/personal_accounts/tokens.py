from datetime import datetime, timedelta, timezone
from typing import Any

import jwt


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def decode_unverified_jwt(token: str | None) -> dict[str, Any]:
    """Decode JWT metadata without verifying signature for local account metadata only."""
    if not token:
        return {}
    try:
        payload = jwt.decode(token, options={"verify_signature": False})
    except jwt.PyJWTError:
        return {}
    return payload if isinstance(payload, dict) else {}


def extract_account_metadata(
    access_token: str | None,
    id_token: str | None,
    fallback_email: str | None = None,
) -> dict[str, str]:
    """Extract non-sensitive account metadata from ID/access token claims."""
    id_claims = decode_unverified_jwt(id_token)
    access_claims = decode_unverified_jwt(access_token)
    claims = {**access_claims, **id_claims}

    email = str(claims.get("email") or fallback_email or "").strip().lower()
    name = str(claims.get("name") or claims.get("given_name") or "").strip()
    provider_account_id = str(claims.get("sub") or claims.get("user_id") or "").strip()
    openai_auth = claims.get("https://api.openai.com/auth")
    if not isinstance(openai_auth, dict):
        openai_auth = {}
    plan_type = str(
        openai_auth.get("chatgpt_plan_type")
        or claims.get("https://api.openai.com/auth/plan_type")
        or claims.get("plan_type")
        or claims.get("account_plan")
        or "unknown"
    ).strip()

    return {
        "email": email,
        "name": name,
        "provider_account_id": provider_account_id,
        "plan_type": plan_type or "unknown",
    }


def resolve_token_expires_at(token_response: dict[str, Any]) -> datetime | None:
    expires_in = token_response.get("expires_in")
    if isinstance(expires_in, int | float) and expires_in > 0:
        return utc_now() + timedelta(seconds=int(expires_in))

    access_claims = decode_unverified_jwt(token_response.get("access_token"))
    exp = access_claims.get("exp")
    if isinstance(exp, int | float) and exp > 0:
        return datetime.fromtimestamp(exp, tz=timezone.utc)
    return None
