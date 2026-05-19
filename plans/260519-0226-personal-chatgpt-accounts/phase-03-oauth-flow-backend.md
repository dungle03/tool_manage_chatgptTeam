# Phase 03: OAuth Flow Backend

Status: ⬜ Pending
Dependencies: Phase 02

## Objective

Implement OAuth-only account adding with local callback.

The UI starts OAuth, the user logs in through the browser, and the callback returns to the local backend.

## Requirements

### Functional

- [x] Add start OAuth endpoint.
- [x] Generate and store OAuth `state`.
- [x] Generate PKCE `code_verifier` and `code_challenge` if required.
- [x] Open/return authorization URL.
- [x] Add callback endpoint.
- [x] Exchange authorization code for tokens.
- [x] Decode token metadata.
- [x] Detect duplicate account and pause for user decision.
- [x] Complete account save after user chooses overwrite/create-new.

### Non-Functional

- [x] OAuth marked experimental in backend config/docs.
- [x] Callback errors are user-readable.
- [x] OAuth state expires and cannot be reused indefinitely.
- [x] Tokens are never logged.

## Proposed Endpoints

```text
POST /api/personal-accounts/oauth/start
GET  /api/personal-accounts/oauth/callback
POST /api/personal-accounts/oauth/resolve-duplicate
```

## OAuth Config

```text
CHATGPT_OAUTH_CLIENT_ID=app_EMoamEEZ73f0CkXaXp7hrann
CHATGPT_OAUTH_AUTH_URL=https://auth.openai.com/oauth/authorize
CHATGPT_OAUTH_TOKEN_URL=https://auth.openai.com/oauth/token
CHATGPT_OAUTH_REDIRECT_URI=http://localhost:8000/api/personal-accounts/oauth/callback
ENABLE_EXPERIMENTAL_CHATGPT_OAUTH=true
```

## OAuth Scopes

```text
openid profile email offline_access
```

## Callback Outcomes

| Outcome               | UI Behavior                      |
| --------------------- | -------------------------------- |
| Success, no duplicate | Add card and show success        |
| Duplicate found       | Show duplicate modal             |
| OAuth denied          | Show add failed message          |
| Token exchange failed | Show add failed message          |
| Feature disabled      | Show experimental OAuth disabled |

## Duplicate Resolution

```text
overwrite_existing
create_new
cancel
```

## Implementation Steps

1. [x] Add OAuth config loader.
2. [x] Add secure random state generation.
3. [x] Add PKCE helper.
4. [x] Add short-lived pending OAuth store.
5. [x] Implement OAuth start endpoint.
6. [x] Implement OAuth callback endpoint.
7. [x] Implement token exchange service.
8. [x] Decode ID/access token metadata.
9. [x] Implement duplicate detection response.
10. [x] Implement duplicate resolution endpoint.

## Files Created/Modified

- `backend/app/routers/personal_accounts.py` - personal account OAuth routes
- `backend/app/services/personal_accounts/config.py` - OAuth config loader
- `backend/app/services/personal_accounts/oauth.py` - OAuth start/callback/token exchange/duplicate flow
- `backend/app/services/personal_accounts/tokens.py` - JWT decode and token metadata helpers
- `backend/app/schemas.py` - OAuth response/request schemas
- `backend/app/main.py` - register router
- `backend/tests/test_personal_accounts_oauth.py` - OAuth backend regression tests

## Test Criteria

- [x] Start endpoint returns valid authorization URL.
- [x] State mismatch is rejected.
- [x] Expired/unknown state is rejected.
- [x] Callback exchange stores account on success.
- [x] Duplicate email returns duplicate decision state.
- [x] No token appears in logs or API responses.

## Notes

Use exact 9router learnings only for behavior pattern, not as direct copy-paste. Keep provider abstraction clean.

---

Next Phase: [Phase 04: Refresh and Account Health Service](./phase-04-refresh-and-account-health-service.md)
