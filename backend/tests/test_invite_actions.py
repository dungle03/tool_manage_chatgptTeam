from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_resend_and_cancel_invite(seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_send_invite(_self, _access_token, _account_id, _email):
        return {"id": "inv_remote_resend"}

    async def fake_delete_invite(_self, _access_token, _account_id, _email):
        return {"ok": True}

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.delete_invite", fake_delete_invite)

    resend = client.post("/api/resend-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"})
    assert resend.status_code == 200
    assert resend.json()["status"] == "pending"

    cancel = client.request("DELETE", "/api/cancel-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"})
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
