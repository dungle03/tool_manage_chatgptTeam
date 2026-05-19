from sqlalchemy.orm import Session

from app.models import PersonalAccount
from app.services.chatgpt import chatgpt_service
from app.services.personal_accounts.serializers import personal_account_to_public
from app.services.personal_accounts.tokens import utc_now


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
        await chatgpt_service.get_account_info(account.access_token)
    except Exception as exc:
        account.status = "die"
        account.last_error_code = "health_check_failed"
        account.last_error_message = str(exc)[:500]
        account.last_checked_at = now
        account.updated_at = now
        session.commit()
        session.refresh(account)
        return personal_account_to_public(account)

    account.status = "live"
    account.last_error_code = None
    account.last_error_message = None
    account.last_checked_at = now
    account.updated_at = now
    session.commit()
    session.refresh(account)
    return personal_account_to_public(account)
