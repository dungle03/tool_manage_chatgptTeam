import asyncio

from app.services.chatgpt import ChatGPTService


class _FakeResponse:
    def __init__(self, status_code, data=None, text=""):
        self.status_code = status_code
        self._data = data if data is not None else {}
        self.text = text

    def json(self):
        return self._data


class _FakeAsyncSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    async def get(self, url, headers=None, cookies=None):
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def post(self, url, headers=None, json=None, cookies=None):
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response

    async def delete(self, url, headers=None, json=None, cookies=None):
        self.calls += 1
        response = self._responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response



def test_get_account_info_filters_team_accounts(monkeypatch):
    service = ChatGPTService()

    async def fake_request(method, path, headers=None, json_data=None, cookies=None, use_base_url=True):
        return {
            "success": True,
            "data": {
                "accounts": {
                    "acc_team": {
                        "account": {"name": "Team A", "plan_type": "team"},
                        "entitlement": {"subscription_plan": "team_monthly", "expires_at": "2026-12-01"},
                    },
                    "acc_plus": {
                        "account": {"name": "Plus", "plan_type": "plus"},
                        "entitlement": {"subscription_plan": "plus"},
                    },
                }
            },
        }

    monkeypatch.setattr(service, "_request", fake_request)

    accounts = asyncio.run(service.get_account_info("access-token"))

    assert len(accounts) == 1
    assert accounts[0]["account_id"] == "acc_team"
    assert accounts[0]["name"] == "Team A"



def test_send_invite_sets_auth_and_account_headers(monkeypatch):
    service = ChatGPTService()
    captured = {}

    async def fake_request(method, path, headers=None, json_data=None, cookies=None, use_base_url=True):
        captured["method"] = method
        captured["path"] = path
        captured["headers"] = headers
        captured["json_data"] = json_data
        return {"success": True, "data": {}}

    monkeypatch.setattr(service, "_request", fake_request)

    asyncio.run(service.send_invite("at_123", "acc_123", "new@company.com"))

    assert captured["method"] == "POST"
    assert captured["path"] == "/accounts/acc_123/invites"
    assert captured["headers"]["Authorization"] == "Bearer at_123"
    assert captured["headers"]["chatgpt-account-id"] == "acc_123"
    assert captured["json_data"]["email_addresses"] == ["new@company.com"]



def test_refresh_access_token_uses_session_cookie(monkeypatch):
    service = ChatGPTService()
    captured = {}

    async def fake_request(method, path, headers=None, json_data=None, cookies=None, use_base_url=True):
        captured["method"] = method
        captured["path"] = path
        captured["cookies"] = cookies
        captured["use_base_url"] = use_base_url
        return {
            "success": True,
            "data": {
                "accessToken": "new-access-token",
                "sessionToken": "new-session-token",
            },
        }

    monkeypatch.setattr(service, "_request", fake_request)

    refreshed = asyncio.run(service.refresh_access_token("session-token", "acc_123"))

    assert captured["method"] == "GET"
    assert "exchange_workspace_token=true" in captured["path"]
    assert "workspace_id=acc_123" in captured["path"]
    assert captured["cookies"]["__Secure-next-auth.session-token"] == "session-token"
    assert captured["use_base_url"] is False
    assert refreshed["access_token"] == "new-access-token"



def test_request_retries_on_server_error(monkeypatch):
    service = ChatGPTService()
    fake_session = _FakeAsyncSession(
        [
            _FakeResponse(500, {"error": "temporary"}),
            _FakeResponse(502, {"error": "temporary"}),
            _FakeResponse(200, {"ok": True}),
        ]
    )

    async def fake_get_session(identifier="default"):
        return fake_session

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(service, "_get_session", fake_get_session)
    monkeypatch.setattr("app.services.chatgpt.asyncio.sleep", fake_sleep)

    result = asyncio.run(service._request("GET", "/accounts/check/v4-2023-04-27", headers={}))

    assert result["success"] is True
    assert fake_session.calls == 3


def test_request_raises_for_unsupported_method(monkeypatch):
    service = ChatGPTService()

    async def fake_get_session(identifier="default"):
        raise AssertionError("_get_session should not be called for unsupported methods")

    monkeypatch.setattr(service, "_get_session", fake_get_session)

    try:
        asyncio.run(service._request("PATCH", "/accounts/check/v4-2023-04-27", headers={}))
        raise AssertionError("Expected ValueError for unsupported method")
    except ValueError as exc:
        assert str(exc) == "Unsupported method: PATCH"


def test_request_returns_contextual_error_when_transport_fails(monkeypatch):
    service = ChatGPTService()
    fake_session = _FakeAsyncSession(
        [
            RuntimeError("socket closed"),
            RuntimeError("socket closed"),
            RuntimeError("socket closed"),
        ]
    )

    async def fake_get_session(identifier="default"):
        return fake_session

    async def fake_sleep(_seconds):
        return None

    monkeypatch.setattr(service, "_get_session", fake_get_session)
    monkeypatch.setattr("app.services.chatgpt.asyncio.sleep", fake_sleep)

    result = asyncio.run(service._request("GET", "/accounts/check/v4-2023-04-27", headers={}))

    assert result["success"] is False
    assert result["status_code"] == 0
    assert result["error"] == (
        "GET https://chatgpt.com/backend-api/accounts/check/v4-2023-04-27 request failed: socket closed"
    )
