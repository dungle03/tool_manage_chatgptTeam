# Phase 05: Personal Accounts API

Status: ⬜ Pending
Dependencies: Phase 04

## Objective

Expose backend endpoints needed by the Personal Accounts frontend tab.

APIs must return useful account status data without returning raw token values.

## Requirements

### Functional

- [x] List personal accounts.
- [x] Get one account detail.
- [x] Start OAuth add/reconnect.
- [x] Resolve duplicate account decision.
- [x] Manually refresh token.
- [x] Manually check account status.
- [x] Delete personal account.
- [x] Return public account response shape.

### Non-Functional

- [x] Never return `access_token`, `refresh_token`, or `id_token`.
- [x] Return consistent action result shape.
- [x] Errors should be readable on UI.
- [x] Existing `/api/workspaces` endpoints stay unchanged.

## Implemented Endpoints

```text
GET    /api/personal-accounts
GET    /api/personal-accounts/{account_id}
DELETE /api/personal-accounts/{account_id}
POST   /api/personal-accounts/{account_id}/refresh
POST   /api/personal-accounts/{account_id}/check
POST   /api/personal-accounts/{account_id}/reconnect/start
POST   /api/personal-accounts/oauth/start
GET    /api/personal-accounts/oauth/callback
POST   /api/personal-accounts/oauth/resolve-duplicate
```

## Public Account Shape

```json
{
  "id": "...",
  "provider": "codex",
  "auth_type": "oauth",
  "email": "user@example.com",
  "name": "User Name",
  "plan_type": "plus",
  "status": "live",
  "is_active": true,
  "token_expires_at": "2026-05-19T10:00:00Z",
  "last_checked_at": "2026-05-19T02:00:00Z",
  "last_refreshed_at": "2026-05-19T02:00:00Z",
  "next_refresh_at": "2026-05-20T02:00:00Z",
  "last_error_code": null,
  "last_error_message": null,
  "oauth_connected": true,
  "requires_relogin": false,
  "created_at": "...",
  "updated_at": "..."
}
```

## Action Result Shape

```json
{
  "ok": true,
  "message": "Account refreshed",
  "account": {},
  "next_action": null
}
```

For duplicate:

```json
{
  "status": "duplicate_detected",
  "duplicate_token": "...",
  "existing_account": {},
  "new_account": {}
}
```

## Implementation Steps

1. [x] Add response schemas.
2. [x] Add list/detail endpoints.
3. [x] Add delete endpoint.
4. [x] Add manual refresh endpoint.
5. [x] Add manual check endpoint.
6. [x] Add reconnect start endpoint.
7. [x] Wire duplicate resolution to OAuth pending state.
8. [x] Add router to app main.
9. [x] Add endpoint tests.

## Files Created/Modified

- `backend/app/routers/personal_accounts.py`
- `backend/app/schemas.py`
- `backend/app/services/personal_accounts/repository.py`
- `backend/tests/test_personal_accounts_api.py`
- `backend/tests/test_personal_accounts_refresh.py`

## Test Criteria

- [x] List endpoint returns accounts without token fields.
- [x] Refresh endpoint returns updated public account.
- [x] Check endpoint updates status fields.
- [x] Delete endpoint removes or deactivates account safely.
- [x] Duplicate response supports UI modal.
- [x] Workspace APIs still pass existing tests.

## Notes

Prefer soft-delete only if existing project convention uses it. Otherwise normal delete is acceptable for local-only data.

---

Next Phase: [Phase 06: Frontend Personal Accounts Tab](./phase-06-frontend-personal-accounts-tab.md)
