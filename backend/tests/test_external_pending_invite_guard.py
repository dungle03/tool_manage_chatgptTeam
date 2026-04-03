from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Invite, UnauthorizedFinding, Workspace


def test_remote_only_pending_invite_is_not_whitelisted_and_is_auto_kicked(
    client, seed_data, monkeypatch
):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    remote_members_state = {
        "members": [
            {
                "id": "user_remote_owner",
                "email": "owner@company.com",
                "name": "Owner",
                "role": "owner",
                "created": "2026-03-09T00:00:00Z",
            },
            {
                "id": "user_remote_1",
                "email": "member1@company.com",
                "name": "Member One",
                "role": "member",
                "created": "2026-03-09T00:00:00Z",
            },
            {
                "id": "user_remote_external",
                "email": "external-pending@company.com",
                "name": "External Pending",
                "role": "member",
                "created": "2026-03-10T00:00:00Z",
            },
        ]
    }

    async def fake_get_members(_self, _access_token, _account_id):
        return remote_members_state["members"]

    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {
                "id": "inv_external_1",
                "email": "external-pending@company.com",
                "status": "pending",
                "created_at": "2026-03-09T00:00:00Z",
            }
        ]

    delete_calls = []

    async def fake_delete_member(_self, _access_token, _account_id, _user_id):
        delete_calls.append((_account_id, _user_id))
        remote_members_state["members"] = [
            member
            for member in remote_members_state["members"]
            if member["id"] != _user_id
        ]
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_members",
        fake_get_members,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_invites",
        fake_get_invites,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.delete_member",
        fake_delete_member,
    )

    session = SessionLocal()
    try:
        session.query(Invite).filter_by(
            org_id="org_001", email="pending@company.com"
        ).delete()
        session.add(
            Invite(
                org_id="org_001",
                email="external-pending@company.com",
                invite_id="inv_external_1",
                status="pending",
                created_by_tool=False,
                created_at=datetime.now(timezone.utc),
            )
        )
        workspace = session.query(Workspace).filter_by(org_id="org_001").one()
        workspace.unauthorized_member_mode = "auto_kick"
        session.commit()
    finally:
        session.close()

    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["unauthorized_detected"] == 1
    assert delete_calls == [("acc_001", "user_remote_external")]

    session = SessionLocal()
    try:
        finding = (
            session.query(UnauthorizedFinding)
            .filter_by(org_id="org_001", remote_id="user_remote_external")
            .one()
        )
        assert finding.email == "external-pending@company.com"
        assert finding.status == "kicked"

        invite = (
            session.query(Invite)
            .filter_by(org_id="org_001", email="external-pending@company.com")
            .one()
        )
        assert invite.created_by_tool is False
    finally:
        session.close()
