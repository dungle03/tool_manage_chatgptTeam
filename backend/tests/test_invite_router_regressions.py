from datetime import datetime, timezone

from app.db import SessionLocal
from app.models import Invite


def test_invite_member_reuses_existing_invite_by_remote_invite_id(
    client, seed_data, monkeypatch
):
    async def fake_send_invite(
        _self, _access_token, _account_id, _email, resend_emails=False
    ):
        assert resend_emails is False
        return {"id": "inv_existing_123"}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite",
        fake_send_invite,
    )

    session = SessionLocal()
    try:
        session.add(
            Invite(
                org_id="org_001",
                email="old-email@company.com",
                invite_id="inv_existing_123",
                status="pending",
                created_by_tool=False,
                created_at=datetime.now(timezone.utc),
            )
        )
        session.commit()
    finally:
        session.close()

    response = client.post(
        "/api/invite",
        json={
            "org_id": "org_001",
            "email": "new-email@company.com",
            "role": "member",
        },
    )
    assert response.status_code == 200, response.text

    session = SessionLocal()
    try:
        invites = (
            session.query(Invite).filter(Invite.invite_id == "inv_existing_123").all()
        )
        assert len(invites) == 1
        assert invites[0].email == "new-email@company.com"
        assert invites[0].created_by_tool is True
    finally:
        session.close()
