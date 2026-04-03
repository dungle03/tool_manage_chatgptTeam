from app.db import SessionLocal
from app.models import Member, UnauthorizedFinding, Workspace


def test_kick_member_blocks_owner(client, seed_data):
    payload = {"org_id": "org_001", "member_id": 2}
    response = client.request("DELETE", "/api/member", json=payload)
    assert response.status_code == 409
    assert response.json()["detail"] == "cannot remove owner"


def test_kick_member_upstream_failure_keeps_local_member(
    client, seed_data, monkeypatch
):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_delete_member(_self, _access_token, _account_id, _user_id):
        raise RuntimeError("upstream delete failed")

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.delete_member",
        fake_delete_member,
    )

    payload = {"org_id": "org_001", "member_id": 1}
    response = client.request("DELETE", "/api/member", json=payload)
    assert response.status_code == 502
    assert "failed to remove member upstream" in response.json()["detail"]

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200
    members = members_response.json()
    assert {member["id"] for member in members} == {1, 2}

    session = SessionLocal()
    try:
        workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        assert workspace.member_count == 2
    finally:
        session.close()


def test_manual_kick_unauthorized_member_marks_finding_kicked(
    client, seed_data, monkeypatch
):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_delete_member(_self, _access_token, _account_id, _user_id):
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.delete_member",
        fake_delete_member,
    )

    session = SessionLocal()
    try:
        session.add(
            UnauthorizedFinding(
                org_id="org_001",
                remote_id="user_remote_1",
                email="member1@company.com",
                name="Member One",
                role="member",
                status="detected",
            )
        )
        session.commit()
        finding_id = (
            session.query(UnauthorizedFinding)
            .filter_by(org_id="org_001", remote_id="user_remote_1")
            .one()
            .id
        )
    finally:
        session.close()

    response = client.post(
        f"/api/workspaces/org_001/unauthorized-members/{finding_id}/kick",
        json={"reason": "manual verification"},
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["action"] == "unauthorized_member_kick"
    assert body["status"] == "kicked"
    assert body["updated_record"]["status"] == "kicked"
    assert body["refresh_hint"]["reason"] == "unauthorized_member_kicked"

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200
    members = members_response.json()
    assert [member["id"] for member in members] == [2]

    session = SessionLocal()
    try:
        finding = (
            session.query(UnauthorizedFinding)
            .filter_by(org_id="org_001", id=finding_id)
            .one()
        )
        workspace = session.query(Workspace).filter(Workspace.org_id == "org_001").one()
        assert finding.status == "kicked"
        assert finding.action_reason == "manual verification"
        assert finding.resolved_at is not None
        assert workspace.member_count == 1
        assert (
            session.query(Member)
            .filter_by(org_id="org_001", remote_id="user_remote_1")
            .one_or_none()
            is None
        )
    finally:
        session.close()
