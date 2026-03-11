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

    list_res = client.get("/api/invites", params={"org_id": "org_001"})
    assert list_res.status_code == 200
    emails = [x["email"] for x in list_res.json()]
    assert "new@company.com" in emails
