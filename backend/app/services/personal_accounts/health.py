import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from app.models import PersonalAccount
from app.services.chatgpt import chatgpt_service
from app.services.personal_accounts.serializers import personal_account_to_public
from app.services.personal_accounts.tokens import utc_now


PLAN_DATE_FIELDS = {"expires_at", "renews_at"}


def parse_chatgpt_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip().replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def apply_personal_plan_entitlement(
    account: PersonalAccount,
    account_info: dict[str, Any],
) -> None:
    account_data = account_info.get("account") or {}
    entitlement = account_info.get("entitlement") or {}

    plan_type = account_data.get("plan_type")
    if isinstance(plan_type, str) and plan_type:
        account.plan_type = plan_type

    subscription_plan = entitlement.get("subscription_plan")
    account.subscription_plan = (
        subscription_plan if isinstance(subscription_plan, str) else None
    )
    account.plan_expires_at = parse_chatgpt_datetime(entitlement.get("expires_at"))
    account.plan_renews_at = parse_chatgpt_datetime(entitlement.get("renews_at"))

    safe_entitlement = {
        key: value
        for key, value in entitlement.items()
        if key in PLAN_DATE_FIELDS
        or key
        in {
            "subscription_plan",
            "billing_period",
            "has_active_subscription",
            "cancels_at",
        }
    }
    account.provider_specific_data = json.dumps(
        {
            "account_id": account_info.get("account_id"),
            "plan_type": account.plan_type,
            "entitlement": safe_entitlement,
        },
        ensure_ascii=False,
    )


async def fetch_personal_plan_entitlement(
    account: PersonalAccount,
) -> dict[str, Any] | None:
    if not account.access_token:
        return None

    result = await chatgpt_service._request(
        "GET",
        "/accounts/check/v4-2023-04-27",
        headers=chatgpt_service._build_headers(access_token=account.access_token),
    )
    if not result.get("success"):
        raise RuntimeError(result.get("error", "failed to fetch account entitlement"))

    accounts = result.get("data", {}).get("accounts", {})
    if not isinstance(accounts, dict):
        return None

    candidates = []
    for account_id, item in accounts.items():
        if not isinstance(item, dict):
            continue
        account_data = item.get("account") or {}
        item = {**item, "account_id": account_id}
        if account_id == account.provider_account_id:
            return item
        if account_id == "default":
            candidates.insert(0, item)
        elif account_data.get("plan_type") in {"plus", "pro", "free"}:
            candidates.append(item)

    return candidates[0] if candidates else None


def mark_need_relogin(
    session: Session,
    account: PersonalAccount,
    error_code: str,
    message: str,
) -> dict:
    now = utc_now()
    account.status = "need_relogin"
    account.last_error_code = error_code
    account.last_error_message = message
    account.reauth_required_at = now
    account.last_checked_at = now
    account.updated_at = now
    session.commit()
    session.refresh(account)
    return personal_account_to_public(account)


async def check_personal_account(
    session: Session,
    account: PersonalAccount,
) -> dict:
    now = utc_now()
    if not account.access_token:
        return mark_need_relogin(
            session,
            account,
            "missing_access_token",
            "Account has no access token. Please reconnect.",
        )

    try:
        plan_info = await fetch_personal_plan_entitlement(account)
    except Exception as exc:
        account.status = "die"
        account.last_error_code = "health_check_failed"
        account.last_error_message = str(exc)[:500]
        account.last_checked_at = now
        account.updated_at = now
        session.commit()
        session.refresh(account)
        return personal_account_to_public(account)

    if plan_info is not None:
        apply_personal_plan_entitlement(account, plan_info)

    account.status = "live"
    account.last_error_code = None
    account.last_error_message = None
    account.last_checked_at = now
    account.updated_at = now
    session.commit()
    session.refresh(account)
    return personal_account_to_public(account)
