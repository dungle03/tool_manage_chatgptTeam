from fastapi import APIRouter

router = APIRouter()


@router.get("/api/invites")
def get_invites(org_id: str):
    return []


@router.post("/api/resend-invite")
def resend_invite(payload: dict):
    return {"ok": True, "payload": payload}


@router.delete("/api/cancel-invite")
def cancel_invite(payload: dict):
    return {"ok": True, "payload": payload}
