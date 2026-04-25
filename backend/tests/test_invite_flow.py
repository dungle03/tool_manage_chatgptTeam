from app.db import SessionLocal
from app.main import app
from app.models import Invite


def test_invite_then_list_invites(client, seed_data, monkeypatch):
    captured_send = {}

    async def fake_send_invite(
        _self, _access_token, _account_id, _email, resend_emails=True
    ):
        captured_send["email"] = _email
        captured_send["resend_emails"] = resend_emails
        return {"id": "inv_remote_created"}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite
    )

    payload = {"org_id": "org_001", "email": "new@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)
    assert create_res.status_code == 200

    body = create_res.json()
    assert body["ok"] is True
    assert body["action"] == "invite_create"
    assert body["invite_id"] == "inv_remote_created"
    assert body["invite"]["invite_id"] == "inv_remote_created"
    assert body["invite"]["created_by_tool"] is True
    assert body["updated_record"]["invite_id"] == "inv_remote_created"
    assert body["updated_record"]["email"] == "new@company.com"
    assert body["updated_record"]["created_by_tool"] is True
    assert body["updated_summary"]["org_id"] == "org_001"
    assert body["refresh_hint"]["scope"] == "workspace_detail"
    assert body["refresh_hint"]["reason"] == "invite_created"
    assert body["refresh_hint"]["include_details"] is True
    assert captured_send == {"email": "new@company.com", "resend_emails": False}

    list_res = client.get("/api/invites", params={"org_id": "org_001"})
    assert list_res.status_code == 200
    invites = {x["email"]: x for x in list_res.json()}
    assert invites["new@company.com"]["created_by_tool"] is True


def test_invite_uses_existing_pending_invite_without_creating_duplicate(
    client, seed_data, monkeypatch
):
    sent_calls = []

    async def fake_send_invite(
        _self, _access_token, _account_id, _email, resend_emails=True
    ):
        sent_calls.append({"email": _email, "resend_emails": resend_emails})
        return {"id": "inv_should_not_happen"}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite
    )

    payload = {"org_id": "org_001", "email": "pending@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)

    assert create_res.status_code == 200
    body = create_res.json()
    assert body["ok"] is True
    assert body["invite_id"] == "inv_seed_1"
    assert body["invite"]["invite_id"] == "inv_seed_1"
    assert body["invite"]["created_by_tool"] is True
    assert body["already_pending"] is True
    assert body["refresh_hint"]["reason"] == "invite_already_pending"
    assert sent_calls == []


def test_invite_uses_remote_listing_when_create_response_has_no_id(
    client, seed_data, monkeypatch
):
    captured_send = {}

    async def fake_send_invite(
        _self, _access_token, _account_id, _email, resend_emails=True
    ):
        captured_send["email"] = _email
        captured_send["resend_emails"] = resend_emails
        return {"ok": True}

    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {"id": "inv_other", "email": "other@company.com", "status": "pending"},
            {
                "id": "inv_remote_resolved",
                "email": "new@company.com",
                "status": "pending",
            },
        ]

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites
    )

    payload = {"org_id": "org_001", "email": "new@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)
    assert create_res.status_code == 200
    assert create_res.json()["invite_id"] == "inv_remote_resolved"
    assert create_res.json()["invite"]["email"] == "new@company.com"
    assert create_res.json()["invite"]["invite_id"] == "inv_remote_resolved"
    assert captured_send == {"email": "new@company.com", "resend_emails": False}


def test_list_invites_preserves_local_pending_tool_invites_when_remote_listing_is_empty(
    client, seed_data, monkeypatch
):
    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites
    )

    session = SessionLocal()
    try:
        invite = Invite(
            org_id="org_001",
            email="tool-created@company.com",
            invite_id="inv_tool_local",
            status="pending",
            created_by_tool=True,
        )
        session.add(invite)
        session.commit()
    finally:
        session.close()

    response = client.get("/api/invites", params={"org_id": "org_001"})
    assert response.status_code == 200
    invites = {item["email"]: item for item in response.json()}
    assert invites["tool-created@company.com"]["invite_id"] == "inv_tool_local"
    assert invites["tool-created@company.com"]["created_by_tool"] is True


def test_list_invites_learns_new_remote_invites_without_dropping_local_pending_tool_invites(
    client, seed_data, monkeypatch
):
    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {
                "id": "inv_remote_new",
                "email": "remote-only@company.com",
                "status": "pending",
            }
        ]

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites
    )

    session = SessionLocal()
    try:
        invite = Invite(
            org_id="org_001",
            email="tool-created@company.com",
            invite_id="inv_tool_local",
            status="pending",
            created_by_tool=True,
        )
        session.add(invite)
        session.commit()
    finally:
        session.close()

    response = client.get(
        "/api/invites", params={"org_id": "org_001", "refresh_remote": True}
    )
    assert response.status_code == 200
    invites = {item["email"]: item for item in response.json()}
    assert "tool-created@company.com" in invites
    assert "remote-only@company.com" in invites
    assert invites["tool-created@company.com"]["created_by_tool"] is True
    assert invites["remote-only@company.com"]["created_by_tool"] is False


def test_list_invites_normalizes_numeric_pending_statuses_from_remote(
    client, seed_data, monkeypatch
):
    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {
                "id": "inv_remote_numeric_pending",
                "email": "numeric-pending@company.com",
                "status": 2,
            }
        ]

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites
    )

    response = client.get(
        "/api/invites", params={"org_id": "org_001", "refresh_remote": True}
    )
    assert response.status_code == 200
    invites = {item["email"]: item for item in response.json()}
    assert invites["numeric-pending@company.com"]["status"] == "pending"

    session = SessionLocal()
    try:
        stored = (
            session.query(Invite)
            .filter(Invite.invite_id == "inv_remote_numeric_pending")
            .one()
        )
        assert stored.status == "pending"
    finally:
        session.close()


def test_invite_reuses_existing_numeric_pending_status_row(
    client, seed_data, monkeypatch
):
    sent_calls = []

    async def fake_send_invite(
        _self, _access_token, _account_id, _email, resend_emails=True
    ):
        sent_calls.append({"email": _email, "resend_emails": resend_emails})
        return {"id": "inv_should_not_be_called"}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite
    )

    session = SessionLocal()
    try:
        invite = Invite(
            org_id="org_001",
            email="numeric-existing@company.com",
            invite_id="inv_numeric_existing",
            status="2",
            created_by_tool=True,
        )
        session.add(invite)
        session.commit()
    finally:
        session.close()

    payload = {
        "org_id": "org_001",
        "email": "numeric-existing@company.com",
        "role": "member",
    }
    create_res = client.post("/api/invite", json=payload)

    assert create_res.status_code == 200
    body = create_res.json()
    assert body["already_pending"] is True
    assert body["invite"]["invite_id"] == "inv_numeric_existing"
    assert body["invite"]["status"] == "pending"
    assert sent_calls == []
