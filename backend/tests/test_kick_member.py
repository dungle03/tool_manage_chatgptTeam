from app.db import SessionLocal
from app.main import app
from app.models import Workspace


def test_kick_member_sets_removed_status(client, seed_data, monkeypatch):
    async def fake_delete_member(_self, _access_token, _account_id, _user_id):
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.delete_member", fake_delete_member
    )

    payload = {"org_id": "org_001", "member_id": 1}
    response = client.request("DELETE", "/api/member", json=payload)
    assert response.status_code == 200

    body = response.json()
    assert body["ok"] is True
    assert body["action"] == "member_kick"
    assert body["status"] == "removed"
    assert body["updated_record"]["id"] == 1
    assert body["updated_record"]["status"] == "removed"
    assert body["updated_summary"]["org_id"] == "org_001"
    assert body["updated_summary"]["member_count"] == 1
    assert body["refresh_hint"]["scope"] == "workspace_detail"
    assert body["refresh_hint"]["reason"] == "member_kicked"
    assert body["refresh_hint"]["include_details"] is True

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200
    members = members_response.json()
    assert [member["id"] for member in members] == [2]
    assert all(member["status"] == "active" for member in members)

    session = SessionLocal()
    try:
        workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        assert workspace.member_count == 1
    finally:
        session.close()
