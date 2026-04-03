"""Test: Accepted invitees must NOT be flagged as unauthorized members.

Scenario:
1. User invites someone via tool → stored as pending invite in local DB
2. That person accepts the invite → appears as a new member on ChatGPT remote
3. Sync runs → the new member should be whitelisted by matching the pending invite email
4. Without fix: sync would flag them as unauthorized and auto-kick them
"""

import asyncio

from app.db import SessionLocal
from app.models import Invite, Member, UnauthorizedFinding, Workspace


def test_accepted_invite_is_not_flagged_unauthorized(client, seed_data, monkeypatch):
    """When a pending invitee accepts and becomes a remote member,
    they should NOT be detected as unauthorized."""

    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        # Remote now includes the invitee who accepted — they are a member
        return [
            {
                "id": "user_remote_owner",
                "email": "owner@company.com",
                "name": "Owner",
                "role": "account-owner",
                "created": "2026-03-09T00:00:00Z",
            },
            {
                "id": "user_remote_1",
                "email": "member1@company.com",
                "name": "Member One",
                "role": "standard-user",
                "created": "2026-03-09T00:00:00Z",
            },
            {
                # This person was invited via tool (pending in invites table)
                # and just accepted — now appears as a remote member
                "id": "user_new_accepted",
                "email": "pending@company.com",
                "name": "Pending Person",
                "role": "standard-user",
                "created": "2026-03-10T00:00:00Z",
            },
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        # No more pending invites — the invite was consumed when accepted
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

    response = client.post("/api/workspaces/org_001/sync")
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True
    assert data["members_synced"] == 3

    # The accepted invitee must NOT be flagged as unauthorized
    assert data["unauthorized_detected"] == 0

    # Verify no unauthorized findings were created
    session = SessionLocal()
    try:
        findings = session.query(UnauthorizedFinding).filter_by(org_id="org_001").all()
        assert len(findings) == 0, (
            f"Expected 0 unauthorized findings but got {len(findings)}: "
            f"{[(f.email, f.status) for f in findings]}"
        )

        # Verify the accepted person is now in the members table
        accepted_member = (
            session.query(Member)
            .filter_by(org_id="org_001", email="pending@company.com")
            .first()
        )
        assert accepted_member is not None
        assert accepted_member.remote_id == "user_new_accepted"

        # Verify the pending invite was cleaned up (member now exists)
        pending_invite = (
            session.query(Invite)
            .filter_by(org_id="org_001", email="pending@company.com")
            .first()
        )
        assert (
            pending_invite is None
        ), "Pending invite should be removed after member accepted"
    finally:
        session.close()
