import asyncio
import base64
import hashlib
import secrets
import threading
from dataclasses import dataclass
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any
from urllib.parse import parse_qs, quote, urlencode, urlparse

import httpx
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.models import PersonalAccount
from app.services.personal_accounts.config import (
    ChatGPTOAuthSettings,
    get_oauth_settings,
)
from app.services.personal_accounts.serializers import personal_account_to_public
from app.services.personal_accounts.tokens import (
    extract_account_metadata,
    resolve_token_expires_at,
    utc_now,
)

OAUTH_PROVIDER = "codex"
OAUTH_AUTH_TYPE = "oauth"


@dataclass
class PendingOAuthState:
    state: str
    code_verifier: str
    created_at: datetime
    expires_at: datetime


@dataclass
class PendingDuplicateAccount:
    duplicate_token: str
    existing_account_id: int
    token_response: dict[str, Any]
    account_metadata: dict[str, str]
    created_at: datetime
    expires_at: datetime


_pending_oauth_states: dict[str, PendingOAuthState] = {}
_pending_duplicates: dict[str, PendingDuplicateAccount] = {}
_callback_server: ThreadingHTTPServer | None = None
_callback_server_lock = threading.Lock()
CALLBACK_HOST = "127.0.0.1"
CALLBACK_PORT = 1455
CALLBACK_PATHS = {"/auth/callback", "/callback"}


def create_pkce_pair() -> tuple[str, str]:
    code_verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    code_challenge = base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")
    return code_verifier, code_challenge


def create_oauth_start() -> dict[str, str | int]:
    settings = get_oauth_settings()
    _ensure_oauth_enabled(settings)
    _prune_expired_states()

    state = secrets.token_urlsafe(32)
    code_verifier, code_challenge = create_pkce_pair()
    now = utc_now()
    pending = PendingOAuthState(
        state=state,
        code_verifier=code_verifier,
        created_at=now,
        expires_at=now + timedelta(seconds=settings.state_ttl_seconds),
    )
    _pending_oauth_states[state] = pending
    _ensure_local_callback_server()

    params = {
        "response_type": "code",
        "client_id": settings.client_id,
        "redirect_uri": settings.redirect_uri,
        "scope": settings.scope,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
        "id_token_add_organizations": "true",
        "codex_cli_simplified_flow": "true",
        "originator": "codex_cli_rs",
        "state": state,
    }
    query_string = urlencode(params, quote_via=quote)
    return {
        "authorization_url": f"{settings.auth_url}?{query_string}",
        "state": state,
        "expires_in": settings.state_ttl_seconds,
    }


async def handle_oauth_callback(
    session: Session,
    code: str,
    state: str,
) -> dict[str, Any]:
    return await _complete_oauth_callback(session=session, code=code, state=state)


async def handle_oauth_callback_url(
    session: Session,
    callback_url: str,
) -> dict[str, Any]:
    parsed = parse_oauth_callback_url(callback_url)
    return await _complete_oauth_callback(
        session=session,
        code=parsed["code"],
        state=parsed["state"],
    )


def parse_oauth_callback_url(callback_url: str) -> dict[str, str]:
    parsed = urlparse(callback_url.strip())
    query = parse_qs(parsed.query)
    code = (query.get("code") or [""])[0].strip()
    state = (query.get("state") or [""])[0].strip()
    error = (query.get("error") or [""])[0].strip()

    if error:
        raise HTTPException(
            status_code=400,
            detail=f"OAuth provider returned an error: {error}",
        )
    if not code or not state:
        raise HTTPException(
            status_code=400,
            detail="Callback URL must include code and state query parameters.",
        )
    return {"code": code, "state": state}


def _render_callback_page(success: bool, message: str) -> bytes:
    color = "#22c55e" if success else "#ef4444"
    icon = "✓" if success else "✕"
    title = "Authentication Successful" if success else "Authentication Failed"
    safe_message = message.replace("<", "&lt;").replace(">", "&gt;")
    event_type = "personal-oauth-success" if success else "personal-oauth-error"
    return f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{title}</title>
<style>
body{{font-family:system-ui;display:flex;align-items:center;justify-content:center;min-height:100vh;margin:0;background:#0b1020;color:#f8fafc}}
.card{{max-width:460px;text-align:center;padding:32px;border:1px solid rgba(148,163,184,.25);border-radius:24px;background:rgba(15,23,42,.92);box-shadow:0 24px 80px rgba(0,0,0,.45)}}
.icon{{width:64px;height:64px;margin:0 auto 16px;border-radius:50%;display:grid;place-items:center;background:{color};color:white;font-size:36px}}
h1{{margin:0 0 10px;font-size:24px}}p{{color:#cbd5e1;line-height:1.5}}a{{display:inline-flex;margin-top:14px;padding:10px 14px;border-radius:999px;background:#38bdf8;color:#03121f;text-decoration:none;font-weight:800}}
</style></head><body><div class="card"><div class="icon">{icon}</div><h1>{title}</h1><p>{safe_message}</p><p id="close-hint">Returning to dashboard...</p><a href="http://localhost:3000/" target="_self">Open dashboard</a></div>
<script>
try {{
  if (window.opener) {{
    window.opener.postMessage({{ type: "{event_type}", message: {safe_message!r} }}, "http://localhost:3000");
    window.opener.focus();
  }}
}} catch (error) {{}}
setTimeout(() => {{ window.close(); }}, 1800);
setTimeout(() => {{ document.getElementById("close-hint").textContent = "If this tab did not close automatically, use the button below."; }}, 2400);
</script></body></html>""".encode(
        "utf-8"
    )


class _OAuthCallbackHandler(BaseHTTPRequestHandler):
    def log_message(self, format: str, *args: Any) -> None:  # noqa: A002
        return

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path not in CALLBACK_PATHS:
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b"Not found")
            return

        query = parse_qs(parsed.query)
        state = (query.get("state") or [""])[0].strip()
        code = (query.get("code") or [""])[0].strip()
        error = (query.get("error") or [""])[0].strip()

        try:
            if error:
                raise HTTPException(
                    status_code=400, detail=f"OAuth provider returned an error: {error}"
                )
            if not code or not state:
                raise HTTPException(
                    status_code=400,
                    detail="Callback URL must include code and state query parameters.",
                )
            db = SessionLocal()
            try:
                result = asyncio.run(
                    _complete_oauth_callback(session=db, code=code, state=state)
                )
            finally:
                db.close()
            status = result.get("status", "success")
            if status == "duplicate_detected":
                message = "OAuth succeeded, but this account already exists. Resolve duplicate in the dashboard."
            else:
                email = (result.get("account") or {}).get("email") or "account"
                message = f"OAuth succeeded. Saved {email} to the vault."
            body = _render_callback_page(True, message)
        except Exception as exc:  # noqa: BLE001
            detail = getattr(exc, "detail", None) or str(exc)
            body = _render_callback_page(False, str(detail))

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def _ensure_local_callback_server() -> None:
    global _callback_server
    with _callback_server_lock:
        if _callback_server is not None:
            return
        try:
            server = ThreadingHTTPServer(
                (CALLBACK_HOST, CALLBACK_PORT), _OAuthCallbackHandler
            )
        except OSError:
            return
        thread = threading.Thread(
            target=server.serve_forever, name="codex-oauth-callback", daemon=True
        )
        thread.start()
        _callback_server = server


async def _complete_oauth_callback(
    session: Session,
    code: str,
    state: str,
) -> dict[str, Any]:
    settings = get_oauth_settings()
    _ensure_oauth_enabled(settings)
    pending = _consume_oauth_state(state)
    token_response = await exchange_authorization_code(
        settings=settings,
        code=code,
        code_verifier=pending.code_verifier,
    )
    metadata = extract_account_metadata(
        token_response.get("access_token"),
        token_response.get("id_token"),
    )
    if not metadata["email"] and not metadata["provider_account_id"]:
        raise HTTPException(
            status_code=502,
            detail="OAuth succeeded but account identity was missing.",
        )

    duplicate = find_duplicate_account(session, metadata)
    if duplicate is not None:
        duplicate_token = _store_pending_duplicate(
            existing_account_id=duplicate.id,
            token_response=token_response,
            account_metadata=metadata,
            ttl_seconds=settings.state_ttl_seconds,
        )
        return {
            "status": "duplicate_detected",
            "duplicate_token": duplicate_token,
            "existing_account": personal_account_to_public(duplicate),
            "new_account": _safe_new_account_preview(metadata),
        }

    account = save_account_from_oauth(session, token_response, metadata)
    return {
        "status": "success",
        "account": personal_account_to_public(account),
    }


async def exchange_authorization_code(
    settings: ChatGPTOAuthSettings,
    code: str,
    code_verifier: str,
) -> dict[str, Any]:
    payload = {
        "grant_type": "authorization_code",
        "client_id": settings.client_id,
        "code": code,
        "redirect_uri": settings.redirect_uri,
        "code_verifier": code_verifier,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(settings.token_url, data=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="OAuth token exchange failed. Please try adding the account again.",
        ) from exc

    if response.status_code >= 400:
        raise HTTPException(
            status_code=502,
            detail="OAuth token exchange was rejected. Please try logging in again.",
        )

    data = response.json()
    if not isinstance(data, dict) or not data.get("access_token"):
        raise HTTPException(
            status_code=502,
            detail="OAuth token exchange returned an invalid response.",
        )
    return data


def find_duplicate_account(
    session: Session,
    metadata: dict[str, str],
) -> PersonalAccount | None:
    email = metadata.get("email")
    provider_account_id = metadata.get("provider_account_id")
    if email:
        duplicate = session.execute(
            select(PersonalAccount).where(
                PersonalAccount.provider == OAUTH_PROVIDER,
                PersonalAccount.email == email,
                PersonalAccount.is_active == True,  # noqa: E712
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            return duplicate

    if provider_account_id:
        return session.execute(
            select(PersonalAccount).where(
                PersonalAccount.provider == OAUTH_PROVIDER,
                PersonalAccount.provider_account_id == provider_account_id,
                PersonalAccount.is_active == True,  # noqa: E712
            )
        ).scalar_one_or_none()
    return None


def save_account_from_oauth(
    session: Session,
    token_response: dict[str, Any],
    metadata: dict[str, str],
    existing_account: PersonalAccount | None = None,
) -> PersonalAccount:
    now = utc_now()
    account = existing_account or PersonalAccount(provider=OAUTH_PROVIDER)
    account.provider = OAUTH_PROVIDER
    account.provider_account_id = metadata.get("provider_account_id") or None
    account.email = metadata.get("email") or "unknown@local"
    account.name = metadata.get("name") or ""
    account.plan_type = metadata.get("plan_type") or "unknown"
    account.status = "live"
    account.auth_type = OAUTH_AUTH_TYPE
    account.access_token = token_response.get("access_token")
    account.refresh_token = token_response.get("refresh_token")
    account.id_token = token_response.get("id_token")
    account.token_expires_at = resolve_token_expires_at(token_response)
    account.refresh_token_updated_at = now if account.refresh_token else None
    account.last_checked_at = now
    account.last_refreshed_at = now
    account.next_refresh_at = account.token_expires_at
    account.last_error_code = None
    account.last_error_message = None
    account.reauth_required_at = None
    account.is_active = True
    account.updated_at = now
    if existing_account is None:
        account.created_at = now
        session.add(account)
    session.commit()
    session.refresh(account)
    return account


def resolve_duplicate(
    session: Session,
    duplicate_token: str,
    decision: str,
) -> dict[str, Any]:
    pending = _consume_pending_duplicate(duplicate_token)
    normalized_decision = decision.strip().lower()

    if normalized_decision == "cancel":
        return {"status": "cancelled"}

    if normalized_decision == "overwrite_existing":
        existing = session.get(PersonalAccount, pending.existing_account_id)
        if existing is None:
            raise HTTPException(status_code=404, detail="Existing account not found.")
        account = save_account_from_oauth(
            session,
            pending.token_response,
            pending.account_metadata,
            existing_account=existing,
        )
        return {"status": "success", "account": personal_account_to_public(account)}

    if normalized_decision == "create_new":
        account = save_account_from_oauth(
            session,
            pending.token_response,
            pending.account_metadata,
        )
        return {"status": "success", "account": personal_account_to_public(account)}

    raise HTTPException(
        status_code=400,
        detail="decision must be one of: overwrite_existing, create_new, cancel",
    )


def _ensure_oauth_enabled(settings: ChatGPTOAuthSettings) -> None:
    if not settings.enabled:
        raise HTTPException(
            status_code=403,
            detail="Experimental ChatGPT OAuth is disabled. Set ENABLE_EXPERIMENTAL_CHATGPT_OAUTH=true to enable it.",
        )


def _consume_oauth_state(state: str) -> PendingOAuthState:
    _prune_expired_states()
    pending = _pending_oauth_states.pop(state, None)
    if pending is None:
        raise HTTPException(
            status_code=400, detail="OAuth state is invalid or expired."
        )
    if pending.expires_at <= utc_now():
        raise HTTPException(status_code=400, detail="OAuth state is expired.")
    return pending


def _store_pending_duplicate(
    existing_account_id: int,
    token_response: dict[str, Any],
    account_metadata: dict[str, str],
    ttl_seconds: int,
) -> str:
    _prune_expired_duplicates()
    duplicate_token = secrets.token_urlsafe(32)
    now = utc_now()
    _pending_duplicates[duplicate_token] = PendingDuplicateAccount(
        duplicate_token=duplicate_token,
        existing_account_id=existing_account_id,
        token_response=token_response,
        account_metadata=account_metadata,
        created_at=now,
        expires_at=now + timedelta(seconds=ttl_seconds),
    )
    return duplicate_token


def _consume_pending_duplicate(duplicate_token: str) -> PendingDuplicateAccount:
    _prune_expired_duplicates()
    pending = _pending_duplicates.pop(duplicate_token, None)
    if pending is None or pending.expires_at <= utc_now():
        raise HTTPException(
            status_code=400,
            detail="Duplicate resolution token is invalid or expired.",
        )
    return pending


def _prune_expired_states() -> None:
    now = utc_now()
    for state, pending in list(_pending_oauth_states.items()):
        if pending.expires_at <= now:
            _pending_oauth_states.pop(state, None)


def _prune_expired_duplicates() -> None:
    now = utc_now()
    for token, pending in list(_pending_duplicates.items()):
        if pending.expires_at <= now:
            _pending_duplicates.pop(token, None)


def _safe_new_account_preview(metadata: dict[str, str]) -> dict[str, str]:
    return {
        "provider": OAUTH_PROVIDER,
        "email": metadata.get("email", ""),
        "name": metadata.get("name", ""),
        "plan_type": metadata.get("plan_type", "unknown"),
    }
