from app.main import app


def test_kick_member_sets_removed_status(client, seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_delete_member(_self, _access_token, _account_id, _user_id):
        return {"ok": True}

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.delete_member", fake_delete_member)

    payload = {"org_id": "org_001", "member_id": 1}
    response = client.request("DELETE", "/api/member", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "removed"
