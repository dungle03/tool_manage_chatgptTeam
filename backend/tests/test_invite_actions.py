import asyncio

from app.main import app
from app.services.chatgpt import ChatGPTService


def test_resend_and_cancel_invite(client, seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_send_invite(_self, _access_token, _account_id, _email):
        return {"id": "inv_remote_resend"}

    captured_cancel = {}

    async def fake_delete_invite(
        _self, _access_token, _account_id, invite_id=None, email=None
    ):
        captured_cancel["invite_id"] = invite_id
        captured_cancel["email"] = email
        return {"ok": True}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.delete_invite", fake_delete_invite
    )

    resend = client.post(
        "/api/resend-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"}
    )
    assert resend.status_code == 200
    resend_body = resend.json()
    assert resend_body["ok"] is True
    assert resend_body["action"] == "invite_resend"
    assert resend_body["status"] == "pending"
    assert resend_body["updated_record"]["invite_id"] == "inv_seed_1"
    assert resend_body["updated_summary"]["org_id"] == "org_001"
    assert resend_body["refresh_hint"]["reason"] == "invite_resend"
    assert resend_body["refresh_hint"]["include_details"] is True

    invites_after_resend = client.get("/api/invites", params={"org_id": "org_001"})
    assert invites_after_resend.status_code == 200
    resend_invites = invites_after_resend.json()
    assert [invite["invite_id"] for invite in resend_invites] == ["inv_seed_1"]
    assert resend_invites[0]["status"] == "pending"

    cancel = client.request(
        "DELETE",
        "/api/cancel-invite",
        json={"org_id": "org_001", "invite_id": "inv_seed_1"},
    )
    assert cancel.status_code == 200
    cancel_body = cancel.json()
    assert cancel_body["ok"] is True
    assert cancel_body["action"] == "invite_cancel"
    assert cancel_body["status"] == "cancelled"
    assert cancel_body["updated_record"]["invite_id"] == "inv_seed_1"
    assert cancel_body["updated_summary"]["org_id"] == "org_001"
    assert cancel_body["refresh_hint"]["reason"] == "invite_cancelled"
    assert cancel_body["refresh_hint"]["include_details"] is True
    assert captured_cancel == {
        "invite_id": "inv_seed_1",
        "email": "pending@company.com",
    }

    invites_after_cancel = client.get("/api/invites", params={"org_id": "org_001"})
    assert invites_after_cancel.status_code == 200
    assert invites_after_cancel.json() == []


def test_resend_invite_falls_back_to_email_when_invite_id_is_stale(
    client, seed_data, monkeypatch
):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    captured_send = {}

    async def fake_send_invite(_self, _access_token, _account_id, _email):
        captured_send["email"] = _email
        return {"id": "inv_remote_resend"}

    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.refresh_access_token",
        fake_refresh_access_token,
    )
    monkeypatch.setattr(
        "app.services.chatgpt.ChatGPTService.send_invite", fake_send_invite
    )

    resend = client.post(
        "/api/resend-invite",
        json={
            "org_id": "org_001",
            "invite_id": "inv_stale_from_dashboard",
            "email": "pending@company.com",
        },
    )

    assert resend.status_code == 200
    resend_body = resend.json()
    assert resend_body["ok"] is True
    assert resend_body["updated_record"]["invite_id"] == "inv_seed_1"
    assert captured_send == {"email": "pending@company.com"}


def test_delete_invite_prefers_id_and_falls_back_to_email(monkeypatch):
    service = ChatGPTService()
    captured_calls = []

    async def fake_request(
        method, path, headers=None, json_data=None, cookies=None, use_base_url=True
    ):
        captured_calls.append({"method": method, "path": path, "json_data": json_data})
        if path.endswith("/invites/inv_remote_123"):
            return {"success": False, "error": "not ready", "status_code": 404}
        if json_data == {"email_address": "pending@company.com"}:
            return {"success": False, "error": "unsupported", "status_code": 400}
        if json_data == {"email_addresses": ["pending@company.com"]}:
            return {"success": True, "data": {"ok": True}}
        return {"success": False, "error": "unsupported", "status_code": 400}

    monkeypatch.setattr(service, "_request", fake_request)

    result = asyncio.run(
        service.delete_invite(
            "at_123",
            "acc_123",
            invite_id="inv_remote_123",
            email="pending@company.com",
        )
    )

    assert result == {"ok": True}
    assert captured_calls == [
        {
            "method": "DELETE",
            "path": "/accounts/acc_123/invites/inv_remote_123",
            "json_data": None,
        },
        {
            "method": "DELETE",
            "path": "/accounts/acc_123/invites",
            "json_data": {"email_address": "pending@company.com"},
        },
        {
            "method": "DELETE",
            "path": "/accounts/acc_123/invites",
            "json_data": {"email_addresses": ["pending@company.com"]},
        },
    ]


def test_delete_invite_treats_missing_upstream_invite_as_success(monkeypatch):
    service = ChatGPTService()
    captured_calls = []

    async def fake_request(
        method, path, headers=None, json_data=None, cookies=None, use_base_url=True
    ):
        captured_calls.append({"method": method, "path": path, "json_data": json_data})
        if path.endswith("/invites/inv_remote_404"):
            return {"success": False, "error": "not ready", "status_code": 404}
        if json_data == {"email_address": "pending@company.com"}:
            return {
                "success": False,
                "error": '{"detail":{"message":"Not allowed"},"detail":{"type":"missing","loc":["body","email_addresses"],"msg":"Field required"},"detail":"invite not found"}',
                "status_code": 405,
            }
        return {"success": False, "error": "unsupported", "status_code": 400}

    monkeypatch.setattr(service, "_request", fake_request)

    result = asyncio.run(
        service.delete_invite(
            "at_123",
            "acc_123",
            invite_id="inv_remote_404",
            email="pending@company.com",
        )
    )

    assert result == {"ok": True, "already_missing": True}
    assert captured_calls == [
        {
            "method": "DELETE",
            "path": "/accounts/acc_123/invites/inv_remote_404",
            "json_data": None,
        },
        {
            "method": "DELETE",
            "path": "/accounts/acc_123/invites",
            "json_data": {"email_address": "pending@company.com"},
        },
    ]
