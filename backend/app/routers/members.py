from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import verify_admin_token
from app.db import get_session
from app.models import Member, Workspace
from app.routers.workspaces import _resolve_access_token
from app.schemas import KickMemberRequest
from app.services.chatgpt import chatgpt_service

router = APIRouter()


@router.delete("/api/member")
async def delete_member(
    payload: KickMemberRequest,
    session: Session = Depends(get_session),
    _token: str = Depends(verify_admin_token),
):
    row = None
    if payload.member_id is not None:
        row = session.execute(
            select(Member).where(
                Member.org_id == payload.org_id,
                Member.id == payload.member_id,
            )
        ).scalar_one_or_none()

    if row is None and payload.user_id:
        row = session.execute(
            select(Member).where(
                Member.org_id == payload.org_id,
                Member.remote_id == payload.user_id,
            )
        ).scalar_one_or_none()

    if not row:
        raise HTTPException(status_code=404, detail="member not found")
    if row.role.lower() == "owner":
        raise HTTPException(status_code=409, detail="cannot remove owner")

    workspace = session.execute(
        select(Workspace).where(Workspace.org_id == payload.org_id)
    ).scalar_one_or_none()
    if not workspace:
        raise HTTPException(status_code=404, detail="workspace not found")

    account_id = workspace.account_id or workspace.org_id
    access_token = await _resolve_access_token(workspace)

    remote_user_id = payload.user_id or row.remote_id
    if remote_user_id:
        try:
            await chatgpt_service.delete_member(
                access_token,
                account_id,
                remote_user_id,
            )
        except Exception as exc:
            raise HTTPException(status_code=502, detail=str(exc)) from exc

    row.status = "removed"
    if workspace.member_count > 0:
        workspace.member_count -= 1
    session.commit()
    return {"ok": True, "member_id": row.id, "status": row.status}
