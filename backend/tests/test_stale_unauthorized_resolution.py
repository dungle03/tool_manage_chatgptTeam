import asyncio

from app.db import SessionLocal
from app.models import UnauthorizedFinding


def test_sync_auto_resolves_stale_finding_for_member_now_whitelisted(
    client, seed_data, monkeypatch
):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

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
            {
                "id": "user_new_accepted",
                "email": "pending@company.com",
                "name": "Accepted Invitee",
                "role": "member",
                "created": "2026-03-10T00:00:00Z",
            },
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

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

    session = SessionLocal()
    try:
        session.add(
            UnauthorizedFinding(
                org_id="org_001",
                remote_id="user_new_accepted",
                email="pending@company.com",
                name="Accepted Invitee",
                role="member",
                status="detected",
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 200
    body = response.json()
    assert body["unauthorized_detected"] == 0, body
    assert body["updated_summary"]["unauthorized_active_count"] == 0, body

    session = SessionLocal()
    try:
        finding = (
            session.query(UnauthorizedFinding)
            .filter_by(org_id="org_001", email="pending@company.com")
            .one()
        )
        assert finding.status == "trusted"
        assert finding.action_reason == "whitelisted_member_auto_resolved"
        assert finding.resolved_at is not None
    finally:
        session.close()
