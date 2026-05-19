from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import PersonalAccount
from app.schemas import (
    PersonalAccountActionOut,
    PersonalAccountOut,
    PersonalOAuthCallbackUrlRequest,
    PersonalOAuthDuplicateResolveRequest,
    PersonalOAuthResultOut,
    PersonalOAuthStartOut,
)
from app.services.personal_accounts.health import check_personal_account
from app.services.personal_accounts.oauth import (
    create_oauth_start,
    handle_oauth_callback,
    handle_oauth_callback_url,
    resolve_duplicate,
)
from app.services.personal_accounts.refresh import refresh_personal_account
from app.services.personal_accounts.repository import (
    get_personal_account,
    list_personal_accounts,
    soft_delete_personal_account,
)
from app.services.personal_accounts.serializers import personal_account_to_public

router = APIRouter(prefix="/api/personal-accounts", tags=["personal-accounts"])


def _get_account_or_404(session: Session, account_id: int) -> PersonalAccount:
    account = get_personal_account(session, account_id)
    if account is None:
        raise HTTPException(status_code=404, detail="Personal account not found.")
    return account


def _action(message: str, account: dict, next_action: str | None = None) -> dict:
    return {
        "ok": True,
        "message": message,
        "account": account,
        "next_action": next_action,
    }


@router.get("", response_model=list[PersonalAccountOut])
def list_accounts(
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    return list_personal_accounts(session)


@router.get("/{account_id}", response_model=PersonalAccountOut)
def get_account_detail(
    account_id: int,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    return personal_account_to_public(_get_account_or_404(session, account_id))


@router.delete("/{account_id}", response_model=PersonalAccountActionOut)
def delete_account(
    account_id: int,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    account = _get_account_or_404(session, account_id)
    public = soft_delete_personal_account(session, account)
    return _action("Account deleted", public)


@router.post("/oauth/start", response_model=PersonalOAuthStartOut)
def start_oauth(_token: str = Depends(verify_admin_token)):
    return create_oauth_start()


@router.get("/oauth/callback", response_model=PersonalOAuthResultOut)
async def oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    session: Session = Depends(get_session),
):
    return await handle_oauth_callback(session=session, code=code, state=state)


@router.post("/oauth/callback-url", response_model=PersonalOAuthResultOut)
async def oauth_callback_url(
    payload: PersonalOAuthCallbackUrlRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    return await handle_oauth_callback_url(
        session=session,
        callback_url=payload.callback_url,
    )


@router.post("/oauth/resolve-duplicate", response_model=PersonalOAuthResultOut)
def resolve_oauth_duplicate(
    payload: PersonalOAuthDuplicateResolveRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    return resolve_duplicate(
        session=session,
        duplicate_token=payload.duplicate_token,
        decision=payload.decision,
    )


@router.post("/{account_id}/refresh", response_model=PersonalAccountActionOut)
async def refresh_account(
    account_id: int,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    account = _get_account_or_404(session, account_id)
    public = await refresh_personal_account(session, account)
    next_action = "reconnect" if public.get("requires_relogin") else None
    return _action("Account refreshed", public, next_action)


@router.post("/{account_id}/check", response_model=PersonalAccountActionOut)
async def check_account(
    account_id: int,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    account = _get_account_or_404(session, account_id)
    public = await check_personal_account(session, account)
    next_action = "reconnect" if public.get("requires_relogin") else None
    return _action("Account checked", public, next_action)


@router.post("/{account_id}/reconnect/start", response_model=PersonalOAuthStartOut)
def reconnect_account(
    account_id: int,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    _get_account_or_404(session, account_id)
    return create_oauth_start()
