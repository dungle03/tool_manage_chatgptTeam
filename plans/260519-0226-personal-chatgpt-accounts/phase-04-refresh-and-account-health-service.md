# Phase 04: Refresh and Account Health Service

Status: ⬜ Pending
Dependencies: Phase 03

## Objective

Implement safe token refresh and account health tracking.

This phase is the core of the feature: keeping accounts marked as `Live`, `Die`, or `Need re-login` without exposing tokens.

## Requirements

### Functional

- [x] Refresh account access token manually.
- [x] Check account health manually.
- [x] Save new refresh token immediately when returned.
- [x] Mark account `Need re-login` on unrecoverable refresh errors.
- [x] Update `last_checked_at`, `last_refreshed_at`, and `next_refresh_at`.
- [x] Keep card visible even when re-login is needed.

### Non-Functional

- [x] Prevent parallel refresh for the same account.
- [x] Do not retry unrecoverable refresh errors blindly.
- [x] Redact token values from all logs/errors.
- [x] Keep refresh logic provider-specific but service interface generic.

## 9router-Inspired Refresh Rules

OpenAI/Codex refresh tokens are rotating one-time-use tokens.

Rules implemented:

```text
1. Only one refresh in-flight per personal account.
2. If a second refresh starts, reuse/wait for the active refresh task.
3. If refresh succeeds and returns refresh_token, store it immediately.
4. If refresh fails with unrecoverable code, mark Need re-login.
5. Do not retry invalid_grant / refresh_token_reused / token_expired / invalid_token.
```

## Unrecoverable Error Codes

```text
refresh_token_reused
invalid_grant
token_expired
invalid_token
invalid_request
```

## Service Interface

```text
refresh_personal_account(session, account) -> AccountPublic
check_personal_account(session, account) -> AccountPublic
mark_need_relogin(session, account, error_code, message) -> AccountPublic
select_due_personal_account_ids(session, limit=None) -> list[int]
```

## Implementation Steps

1. [x] Add per-account in-flight refresh lock.
2. [x] Add Codex refresh token request.
3. [x] Add refresh result parser.
4. [x] Add unrecoverable error detector.
5. [x] Add safe DB update transaction for rotated token.
6. [x] Add account health status update logic.
7. [x] Add manual check logic.
8. [x] Add optional scheduler hooks for future auto refresh.
9. [x] Add tests for successful refresh.
10. [x] Add tests for unrecoverable refresh failure.
11. [x] Add tests for concurrent refresh de-duplication.

## Files Created/Modified

- `backend/app/services/personal_accounts/refresh.py` - refresh manager
- `backend/app/services/personal_accounts/health.py` - status/check logic
- `backend/app/services/personal_accounts/redaction.py` - log redaction helpers
- `backend/app/routers/personal_accounts.py` - refresh/check endpoints
- `backend/tests/test_personal_accounts_refresh.py` - refresh and health tests

## Test Criteria

- [x] Successful refresh updates access token and rotated refresh token.
- [x] Missing refresh token marks `Need re-login`.
- [x] `invalid_grant` marks `Need re-login` and does not retry.
- [x] Parallel refresh calls for same account perform one upstream refresh.
- [x] Tokens are not emitted in logs/test response snapshots.

## Notes

Auto refresh can be prepared here but does not need to run on a schedule until Phase 2 unless simple to integrate safely.

---

Next Phase: [Phase 05: Personal Accounts API](./phase-05-personal-accounts-api.md)
