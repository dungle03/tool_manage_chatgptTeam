from fastapi import APIRouter

router = APIRouter()


@router.get("/api/workspaces")
def get_workspaces():
    return []


@router.get("/api/workspaces/{id}/members")
def get_workspace_members(id: str):
    return []
