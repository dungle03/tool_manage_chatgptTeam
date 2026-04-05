from app.db import SessionLocal
from app.models import Member, UnauthorizedFinding, Workspace


def test_existing_local_member_is_whitelisted_on_sync(client, seed_data, monkeypatch):
    async def fake_get_members(_self, _access_token, _account_id):
        return [
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
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_members",
        fake_get_members,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_invites",
        fake_get_invites,
    )

    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["unauthorized_detected"] == 0
    assert body["updated_summary"]["unauthorized_active_count"] == 0

    session = SessionLocal()
    try:
        findings = session.query(UnauthorizedFinding).filter_by(org_id="org_001").all()
        assert findings == []
    finally:
        session.close()


def test_auto_kick_detects_and_removes_truly_unauthorized_member(
    client, seed_data, monkeypatch
):
    async def fake_get_members(_self, _access_token, _account_id):
        return [
            {
                "id": "user_remote_owner",
                "email": "owner@company.com",
                "name": "Owner",
                "role": "owner",
                "created": "2026-03-09T00:00:00Z",
            },
            {
                "id": "user_remote_intruder",
                "email": "intruder@evil.com",
                "name": "Intruder",
                "role": "member",
                "created": "2026-03-10T00:00:00Z",
            },
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    delete_calls = []

    async def fake_delete_member(_self, _access_token, _account_id, _user_id):
        delete_calls.append((_account_id, _user_id))
        return {"ok": True}

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
        workspace = session.query(Workspace).filter_by(org_id="org_001").one()
        workspace.unauthorized_member_mode = "auto_kick"
        session.commit()
    finally:
        session.close()

    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["unauthorized_detected"] == 1
    assert delete_calls == [("acc_001", "user_remote_intruder")]

    session = SessionLocal()
    try:
        finding = (
            session.query(UnauthorizedFinding)
            .filter_by(org_id="org_001", remote_id="user_remote_intruder")
            .one()
        )
        assert finding.email == "intruder@evil.com"
        assert finding.status == "kicked"
        assert finding.action_reason == "auto_kick_sync_enforcement"
        assert finding.resolved_at is not None

        intruder_member = (
            session.query(Member)
            .filter_by(org_id="org_001", remote_id="user_remote_intruder")
            .one_or_none()
        )
        assert intruder_member is None
    finally:
        session.close()
