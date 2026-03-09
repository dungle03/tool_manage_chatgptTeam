from fastapi import APIRouter

router = APIRouter()


@router.post("/api/invite")
def invite_member(payload: dict):
    return {"ok": True, "payload": payload}


@router.delete("/api/member")
def delete_member(payload: dict):
    return {"ok": True, "payload": payload}
