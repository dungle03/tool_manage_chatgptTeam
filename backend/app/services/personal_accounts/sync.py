import asyncio
import os
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PersonalAccount
from app.services.personal_accounts.health import (
    apply_personal_plan_entitlement,
    fetch_personal_plan_entitlement,
)
from app.services.personal_accounts.refresh import refresh_personal_account
from app.services.personal_accounts.serializers import personal_account_to_public
from app.services.personal_accounts.tokens import utc_now

PERSONAL_PLAN_SYNC_STALE_HOURS = int(os.getenv("PERSONAL_PLAN_SYNC_STALE_HOURS", "6"))
PERSONAL_PLAN_SYNC_BATCH_SIZE = int(os.getenv("PERSONAL_PLAN_SYNC_BATCH_SIZE", "5"))
PERSONAL_PLAN_SYNC_DELAY_SECONDS = float(
    os.getenv("PERSONAL_PLAN_SYNC_DELAY_SECONDS", "2")
)
PERSONAL_PLAN_SYNC_RETRY_MINUTES = int(
    os.getenv("PERSONAL_PLAN_SYNC_RETRY_MINUTES", "45")
)
PERSONAL_PLAN_SYNC_AUTH_ERRORS = ("401", "unauthorized", "invalid token", "expired")

_PLAN_SYNC_LOCKS: dict[int, asyncio.Lock] = {}


def _get_plan_sync_lock(account_id: int) -> asyncio.Lock:
    lock = _PLAN_SYNC_LOCKS.get(account_id)
    if lock is None:
        lock = asyncio.Lock()
        _PLAN_SYNC_LOCKS[account_id] = lock
    return lock


def is_personal_plan_sync_in_progress(account_id: int) -> bool:
    return _get_plan_sync_lock(account_id).locked()


def _default_next_sync_at():
    return utc_now() + timedelta(hours=PERSONAL_PLAN_SYNC_STALE_HOURS)


def _retry_next_sync_at():
    return utc_now() + timedelta(minutes=PERSONAL_PLAN_SYNC_RETRY_MINUTES)


def _is_auth_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in PERSONAL_PLAN_SYNC_AUTH_ERRORS)


def _as_aware_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def select_due_personal_plan_sync_account_ids(
    session: Session,
    *,
    limit: int = PERSONAL_PLAN_SYNC_BATCH_SIZE,
    force: bool = False,
) -> list[int]:
    now = utc_now()
    rows = (
        session.execute(
            select(PersonalAccount).where(
                PersonalAccount.is_active.is_(True),
                PersonalAccount.access_token.is_not(None),
                PersonalAccount.status != "need_relogin",
            )
        )
        .scalars()
        .all()
    )

    due: list[int] = []
    for account in rows:
        if account.id is None or is_personal_plan_sync_in_progress(account.id):
            continue
        next_sync_at = _as_aware_utc(account.next_plan_sync_at)
        if force or next_sync_at is None or next_sync_at <= now:
            due.append(account.id)
        if len(due) >= limit:
            break
    return due


async def sync_personal_plan_account(
    session: Session,
    account: PersonalAccount,
    *,
    trigger: str = "manual",
) -> dict[str, Any]:
    if account.id is None:
        raise ValueError("personal account must be persisted before sync")

    lock = _get_plan_sync_lock(account.id)
    if lock.locked():
        return {
            "ok": True,
            "account_id": account.id,
            "email": account.email,
            "already_in_progress": True,
            "account": personal_account_to_public(account),
        }

    async with lock:
        now = utc_now()
        account.last_plan_sync_at = now
        account.plan_sync_error = None
        account.updated_at = now
        session.commit()

        try:
            plan_info = await fetch_personal_plan_entitlement(account)
            if plan_info is not None:
                apply_personal_plan_entitlement(account, plan_info)
            account.status = "live"
            account.plan_sync_error = None
            account.plan_sync_fail_count = 0
            account.last_checked_at = utc_now()
            account.last_plan_sync_at = account.last_checked_at
            account.next_plan_sync_at = _default_next_sync_at()
            account.updated_at = account.last_checked_at
            session.commit()
            session.refresh(account)
            return {
                "ok": True,
                "account_id": account.id,
                "email": account.email,
                "trigger": trigger,
                "account": personal_account_to_public(account),
            }
        except Exception as exc:
            message = str(exc)[:500]
            if _is_auth_error(message) and account.refresh_token:
                try:
                    await refresh_personal_account(session, account)
                    session.refresh(account)
                    plan_info = await fetch_personal_plan_entitlement(account)
                    if plan_info is not None:
                        apply_personal_plan_entitlement(account, plan_info)
                    account.status = "live"
                    account.plan_sync_error = None
                    account.plan_sync_fail_count = 0
                    account.last_checked_at = utc_now()
                    account.last_plan_sync_at = account.last_checked_at
                    account.next_plan_sync_at = _default_next_sync_at()
                    account.updated_at = account.last_checked_at
                    session.commit()
                    session.refresh(account)
                    return {
                        "ok": True,
                        "account_id": account.id,
                        "email": account.email,
                        "trigger": trigger,
                        "refreshed_token": True,
                        "account": personal_account_to_public(account),
                    }
                except Exception as refresh_exc:
                    message = str(refresh_exc)[:500]

            session.rollback()
            managed = session.get(PersonalAccount, account.id)
            if managed is None:
                raise
            managed.plan_sync_error = message
            managed.plan_sync_fail_count = (managed.plan_sync_fail_count or 0) + 1
            managed.last_plan_sync_at = utc_now()
            managed.next_plan_sync_at = _retry_next_sync_at()
            managed.updated_at = managed.last_plan_sync_at
            session.commit()
            session.refresh(managed)
            return {
                "ok": False,
                "account_id": managed.id,
                "email": managed.email,
                "trigger": trigger,
                "error": message,
                "account": personal_account_to_public(managed),
            }


async def sync_due_personal_plan_accounts(
    session_factory: Any,
    *,
    limit: int = PERSONAL_PLAN_SYNC_BATCH_SIZE,
    force: bool = False,
    trigger: str = "background",
) -> dict[str, Any]:
    with session_factory() as session:
        ids = select_due_personal_plan_sync_account_ids(
            session, limit=limit, force=force
        )

    results: list[dict[str, Any]] = []
    for index, account_id in enumerate(ids):
        with session_factory() as session:
            account = session.get(PersonalAccount, account_id)
            if account is not None:
                results.append(
                    await sync_personal_plan_account(session, account, trigger=trigger)
                )
        if index < len(ids) - 1 and PERSONAL_PLAN_SYNC_DELAY_SECONDS > 0:
            await asyncio.sleep(PERSONAL_PLAN_SYNC_DELAY_SECONDS)

    return {
        "ok": True,
        "trigger": trigger,
        "selected": len(ids),
        "synced": sum(1 for item in results if item.get("ok")),
        "failed": sum(1 for item in results if not item.get("ok")),
        "results": results,
    }


async def run_personal_plan_sync_cycle(session_factory: Any) -> None:
    await sync_due_personal_plan_accounts(session_factory, trigger="background")
