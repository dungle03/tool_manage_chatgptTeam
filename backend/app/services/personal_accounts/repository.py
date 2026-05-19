from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import PersonalAccount
from app.services.personal_accounts.serializers import personal_account_to_public
from app.services.personal_accounts.tokens import utc_now


def list_personal_accounts(session: Session) -> list[dict]:
    accounts = (
        session.execute(
            select(PersonalAccount)
            .where(PersonalAccount.is_active.is_(True))
            .order_by(PersonalAccount.created_at.desc(), PersonalAccount.id.desc())
        )
        .scalars()
        .all()
    )
    return [personal_account_to_public(account) for account in accounts]


def get_personal_account(session: Session, account_id: int) -> PersonalAccount | None:
    account = session.get(PersonalAccount, account_id)
    if account is None or not account.is_active:
        return None
    return account


def soft_delete_personal_account(session: Session, account: PersonalAccount) -> dict:
    now = utc_now()
    account.is_active = False
    account.status = "deleted"
    account.updated_at = now
    account.last_error_code = None
    account.last_error_message = None
    session.commit()
    session.refresh(account)
    return personal_account_to_public(account)
