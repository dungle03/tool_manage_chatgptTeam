import asyncio
import random
from typing import Any

import jwt
from curl_cffi.requests import AsyncSession


class ChatGPTService:
    BASE_URL = "https://chatgpt.com/backend-api"
    MAX_RETRIES = 3
    RETRY_DELAYS = [1, 2, 4]

    def __init__(self) -> None:
        self._sessions: dict[str, AsyncSession] = {}
        self._loop_id: int | None = None

    async def _get_session(self, identifier: str = "default") -> AsyncSession:
        loop_id = id(asyncio.get_running_loop())
        if self._loop_id is not None and self._loop_id != loop_id:
            for session in self._sessions.values():
                try:
                    await session.close()
                except Exception:
                    pass
            self._sessions.clear()
        self._loop_id = loop_id

        if identifier not in self._sessions:
            self._sessions[identifier] = AsyncSession(
                impersonate="chrome110",
                timeout=30,
            )
        return self._sessions[identifier]

    def _build_headers(
        self,
        access_token: str | None = None,
        account_id: str | None = None,
        extra: dict[str, str] | None = None,
    ) -> dict[str, str]:
        headers: dict[str, str] = {
            "Accept": "*/*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://chatgpt.com/",
            "Origin": "https://chatgpt.com",
            "Connection": "keep-alive",
        }
        if access_token:
            headers["Authorization"] = f"Bearer {access_token}"
        if account_id:
            headers["chatgpt-account-id"] = account_id
        if extra:
            headers.update(extra)
        return headers

    async def _request(
        self,
        method: str,
        path: str,
        headers: dict[str, str] | None = None,
        json_data: dict[str, Any] | None = None,
        cookies: dict[str, str] | None = None,
        use_base_url: bool = True,
    ) -> dict[str, Any]:
        session = await self._get_session()
        url = f"{self.BASE_URL}{path}" if use_base_url else path
        request_headers = headers or {}

        for attempt in range(self.MAX_RETRIES):
            try:
                if method == "GET":
                    response = await session.get(
                        url, headers=request_headers, cookies=cookies
                    )
                elif method == "POST":
                    response = await session.post(
                        url,
                        headers=request_headers,
                        json=json_data,
                        cookies=cookies,
                    )
                elif method == "DELETE":
                    response = await session.delete(
                        url,
                        headers=request_headers,
                        json=json_data,
                        cookies=cookies,
                    )
                else:
                    raise ValueError(f"Unsupported method: {method}")

                if 200 <= response.status_code < 300:
                    try:
                        return {"success": True, "data": response.json()}
                    except Exception:
                        return {"success": True, "data": {}}

                if response.status_code >= 500 and attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt] + random.uniform(0.5, 1.5)
                    await asyncio.sleep(delay)
                    continue

                return {
                    "success": False,
                    "error": response.text,
                    "status_code": response.status_code,
                }
            except Exception as exc:
                if attempt < self.MAX_RETRIES - 1:
                    delay = self.RETRY_DELAYS[attempt] + random.uniform(0.5, 1.5)
                    await asyncio.sleep(delay)
                    continue
                return {"success": False, "error": str(exc), "status_code": 0}

        return {"success": False, "error": "unknown error", "status_code": 0}

    async def refresh_access_token(
        self,
        session_token: str,
        account_id: str | None = None,
    ) -> dict[str, str]:
        url = "https://chatgpt.com/api/auth/session"
        if account_id:
            url += f"?exchange_workspace_token=true&workspace_id={account_id}"

        result = await self._request(
            "GET",
            url,
            headers=self._build_headers(extra={"Accept": "application/json"}),
            cookies={"__Secure-next-auth.session-token": session_token},
            use_base_url=False,
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "failed to refresh access token"))

        payload = result["data"]
        access_token = payload.get("accessToken")
        if not access_token:
            raise RuntimeError("accessToken missing from refresh response")

        return {
            "access_token": access_token,
            "session_token": payload.get("sessionToken") or session_token,
        }

    async def get_account_info(self, access_token: str) -> list[dict[str, Any]]:
        result = await self._request(
            "GET",
            "/accounts/check/v4-2023-04-27",
            headers=self._build_headers(access_token=access_token),
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "failed to fetch accounts"))

        accounts = result["data"].get("accounts", {})
        team_accounts: list[dict[str, Any]] = []
        for account_id, info in accounts.items():
            account_data = info.get("account", {})
            entitlement = info.get("entitlement", {})
            if account_data.get("plan_type") != "team":
                continue

            team_accounts.append(
                {
                    "account_id": account_id,
                    "name": account_data.get("name", ""),
                    "plan_type": "team",
                    "subscription_plan": entitlement.get("subscription_plan", ""),
                    "expires_at": entitlement.get("expires_at"),
                    "member_limit": entitlement.get("max_users")
                    or account_data.get("max_users")
                    or 0,
                }
            )
        return team_accounts

    async def get_members(
        self, access_token: str, account_id: str
    ) -> list[dict[str, Any]]:
        all_items: list[dict[str, Any]] = []
        limit = 50
        offset = 0

        while True:
            result = await self._request(
                "GET",
                f"/accounts/{account_id}/users?limit={limit}&offset={offset}",
                headers=self._build_headers(access_token=access_token),
            )
            if not result["success"]:
                raise RuntimeError(result.get("error", "failed to fetch members"))

            data = result["data"]
            items = data.get("items", [])
            total = data.get("total", len(items))
            all_items.extend(items)

            if len(all_items) >= total or not items:
                break
            offset += limit

        return all_items

    async def get_invites(
        self, access_token: str, account_id: str
    ) -> list[dict[str, Any]]:
        result = await self._request(
            "GET",
            f"/accounts/{account_id}/invites",
            headers=self._build_headers(
                access_token=access_token, account_id=account_id
            ),
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "failed to fetch invites"))
        return result["data"].get("items", [])

    async def send_invite(
        self, access_token: str, account_id: str, email: str
    ) -> dict[str, Any]:
        result = await self._request(
            "POST",
            f"/accounts/{account_id}/invites",
            headers=self._build_headers(
                access_token=access_token,
                account_id=account_id,
                extra={"Content-Type": "application/json"},
            ),
            json_data={
                "email_addresses": [email],
                "role": "standard-user",
                "resend_emails": True,
            },
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "failed to send invite"))
        return result["data"]

    async def delete_invite(
        self, access_token: str, account_id: str, email: str
    ) -> dict[str, Any]:
        result = await self._request(
            "DELETE",
            f"/accounts/{account_id}/invites",
            headers=self._build_headers(
                access_token=access_token,
                account_id=account_id,
                extra={"Content-Type": "application/json"},
            ),
            json_data={"email_address": email},
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "failed to delete invite"))
        return result["data"]

    async def delete_member(
        self, access_token: str, account_id: str, user_id: str
    ) -> dict[str, Any]:
        result = await self._request(
            "DELETE",
            f"/accounts/{account_id}/users/{user_id}",
            headers=self._build_headers(
                access_token=access_token, account_id=account_id
            ),
        )
        if not result["success"]:
            raise RuntimeError(result.get("error", "failed to delete member"))
        return result["data"]

    def decode_access_token_claims(self, access_token: str) -> dict[str, Any]:
        return jwt.decode(
            access_token,
            options={"verify_signature": False},
            algorithms=["HS256", "RS256"],
        )

    def extract_email(self, access_token: str) -> str | None:
        claims = self.decode_access_token_claims(access_token)
        auth_claims = claims.get("https://api.openai.com/auth") or {}
        return (
            claims.get("email")
            or claims.get("https://auth.openai.com/email")
            or auth_claims.get("email")
        )

    def extract_user_id(self, access_token: str) -> str | None:
        claims = self.decode_access_token_claims(access_token)
        auth_claims = claims.get("https://api.openai.com/auth") or {}
        return (
            auth_claims.get("chatgpt_user_id")
            or auth_claims.get("user_id")
            or claims.get("user_id")
            or claims.get("sub")
        )


chatgpt_service = ChatGPTService()
