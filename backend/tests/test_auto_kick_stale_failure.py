from app.db import SessionLocal
from app.models import UnauthorizedFinding


def test_missing_kick_failed_finding_is_no_longer_counted_active(
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

    session = SessionLocal()
    try:
        session.add(
            UnauthorizedFinding(
                org_id="org_001",
                remote_id="user_missing_failed",
                email="missing-failed@company.com",
                name="Missing Failed",
                role="member",
                status="kick_failed",
                action_reason="temporary upstream failure",
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["updated_summary"]["unauthorized_active_count"] == 0, body

    session = SessionLocal()
    try:
        finding = (
            session.query(UnauthorizedFinding)
            .filter_by(org_id="org_001", remote_id="user_missing_failed")
            .one()
        )
        assert finding.resolved_at is not None
        assert finding.status not in {"detected", "kick_failed"}
    finally:
        session.close()
