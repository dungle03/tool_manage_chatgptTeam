import asyncio
from datetime import timedelta
from typing import Any

import httpx
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import PersonalAccount
from app.services.personal_accounts.config import get_oauth_settings
from app.services.personal_accounts.health import mark_need_relogin
from app.services.personal_accounts.redaction import compact_error_message
from app.services.personal_accounts.serializers import personal_account_to_public
from app.services.personal_accounts.tokens import resolve_token_expires_at, utc_now

UNRECOVERABLE_REFRESH_ERRORS = {
    "refresh_token_reused",
    "invalid_grant",
    "token_expired",
    "invalid_token",
    "invalid_request",
}

_REFRESH_LOCKS: dict[int, asyncio.Lock] = {}
_REFRESH_TASKS: dict[int, asyncio.Task[dict]] = {}


def get_refresh_lock(account_id: int) -> asyncio.Lock:
    lock = _REFRESH_LOCKS.get(account_id)
    if lock is None:
        lock = asyncio.Lock()
        _REFRESH_LOCKS[account_id] = lock
    return lock


def is_unrecoverable_refresh_error(error_code: str | None) -> bool:
    return bool(error_code and error_code in UNRECOVERABLE_REFRESH_ERRORS)


def parse_refresh_error(
    response_json: Any, fallback_status_code: int | None = None
) -> tuple[str, str]:
    if isinstance(response_json, dict):
        error = response_json.get("error")
        if isinstance(error, dict):
            code = str(error.get("code") or error.get("type") or "refresh_failed")
            message = str(error.get("message") or code)
            return code, message
        if isinstance(error, str):
            return error, str(response_json.get("error_description") or error)
        code = str(response_json.get("code") or "refresh_failed")
        message = str(response_json.get("message") or code)
        return code, message
    return "refresh_failed", f"Refresh failed with status {fallback_status_code or 0}"


async def exchange_refresh_token(refresh_token: str) -> dict[str, Any]:
    settings = get_oauth_settings()
    payload = {
        "grant_type": "refresh_token",
        "client_id": settings.client_id,
        "refresh_token": refresh_token,
    }
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(settings.token_url, data=payload)
    except httpx.HTTPError as exc:
        raise HTTPException(
            status_code=502,
            detail="Refresh request failed. Please try again later.",
        ) from exc

    try:
        data = response.json()
    except ValueError:
        data = {}

    if response.status_code >= 400:
        code, message = parse_refresh_error(data, response.status_code)
        raise HTTPException(
            status_code=400 if is_unrecoverable_refresh_error(code) else 502,
            detail={"code": code, "message": compact_error_message(message)},
        )

    if not isinstance(data, dict) or not data.get("access_token"):
        raise HTTPException(
            status_code=502,
            detail={
                "code": "invalid_refresh_response",
                "message": "Invalid refresh response.",
            },
        )
    return data


async def refresh_personal_account(session: Session, account: PersonalAccount) -> dict:
    if account.id is None:
        raise HTTPException(
            status_code=400, detail="Account must be saved before refresh."
        )

    existing_task = _REFRESH_TASKS.get(account.id)
    if existing_task is not None and not existing_task.done():
        return await existing_task

    task = asyncio.create_task(_refresh_personal_account_locked(session, account.id))
    _REFRESH_TASKS[account.id] = task
    try:
        return await task
    finally:
        if _REFRESH_TASKS.get(account.id) is task:
            _REFRESH_TASKS.pop(account.id, None)


async def _refresh_personal_account_locked(session: Session, account_id: int) -> dict:
    lock = get_refresh_lock(account_id)
    async with lock:
        account = session.get(PersonalAccount, account_id)
        if account is None:
            raise HTTPException(status_code=404, detail="Personal account not found.")
        if not account.refresh_token:
            return mark_need_relogin(
                session,
                account,
                "missing_refresh_token",
                "Account has no refresh token. Please reconnect.",
            )

        account.status = "refreshing"
        account.updated_at = utc_now()
        session.commit()

        try:
            token_response = await exchange_refresh_token(account.refresh_token)
        except HTTPException as exc:
            detail = exc.detail if isinstance(exc.detail, dict) else {}
            code = str(detail.get("code") or "refresh_failed")
            message = str(detail.get("message") or exc.detail)
            if is_unrecoverable_refresh_error(code) or exc.status_code == 400:
                return mark_need_relogin(session, account, code, message)

            now = utc_now()
            account.status = "die"
            account.last_error_code = code
            account.last_error_message = compact_error_message(message)
            account.last_checked_at = now
            account.updated_at = now
            session.commit()
            session.refresh(account)
            return personal_account_to_public(account)

        now = utc_now()
        account.access_token = token_response.get("access_token")
        if token_response.get("refresh_token"):
            account.refresh_token = token_response.get("refresh_token")
            account.refresh_token_updated_at = now
        if token_response.get("id_token"):
            account.id_token = token_response.get("id_token")
        account.token_expires_at = resolve_token_expires_at(token_response)
        account.last_refreshed_at = now
        account.last_checked_at = now
        account.next_refresh_at = _resolve_next_refresh_at(account.token_expires_at)
        account.status = "live"
        account.last_error_code = None
        account.last_error_message = None
        account.reauth_required_at = None
        account.updated_at = now
        session.commit()
        session.refresh(account)
        return personal_account_to_public(account)


def _resolve_next_refresh_at(expires_at):
    if expires_at is None:
        return utc_now() + timedelta(hours=1)
    return max(utc_now(), expires_at - timedelta(minutes=10))


def select_due_personal_account_ids(
    session: Session, *, limit: int | None = None
) -> list[int]:
    now = utc_now()
    rows = (
        session.query(PersonalAccount).filter(PersonalAccount.is_active.is_(True)).all()
    )
    due = [
        row.id
        for row in rows
        if row.id is not None
        and row.status != "need_relogin"
        and row.next_refresh_at
        and row.next_refresh_at <= now
    ]
    due.sort()
    return due[:limit] if limit is not None else due
