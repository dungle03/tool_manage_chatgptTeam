from app.main import app


def test_invite_then_list_invites(client, seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_send_invite(_self, _access_token, _account_id, _email):
        return {"id": "inv_remote_created"}

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite)

    payload = {"org_id": "org_001", "email": "new@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)
    assert create_res.status_code == 200

    body = create_res.json()
    assert body["ok"] is True
    assert body["action"] == "invite_create"
    assert body["invite_id"] == "inv_remote_created"
    assert body["invite"]["invite_id"] == "inv_remote_created"
    assert body["updated_record"]["invite_id"] == "inv_remote_created"
    assert body["updated_record"]["email"] == "new@company.com"
    assert body["updated_summary"]["org_id"] == "org_001"
    assert body["refresh_hint"]["scope"] == "workspace_detail"
    assert body["refresh_hint"]["reason"] == "invite_created"
    assert body["refresh_hint"]["include_details"] is True

    list_res = client.get("/api/invites", params={"org_id": "org_001"})
    assert list_res.status_code == 200
    emails = [x["email"] for x in list_res.json()]
    assert "new@company.com" in emails


def test_invite_uses_remote_listing_when_create_response_has_no_id(client, seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_send_invite(_self, _access_token, _account_id, _email):
        return {"ok": True}

    async def fake_get_invites(_self, _access_token, _account_id):
        return [
            {"id": "inv_other", "email": "other@company.com", "status": "pending"},
            {"id": "inv_remote_resolved", "email": "new@company.com", "status": "pending"},
        ]

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    payload = {"org_id": "org_001", "email": "new@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)
    assert create_res.status_code == 200
    assert create_res.json()["invite_id"] == "inv_remote_resolved"
    assert create_res.json()["invite"]["email"] == "new@company.com"
    assert create_res.json()["invite"]["invite_id"] == "inv_remote_resolved"
