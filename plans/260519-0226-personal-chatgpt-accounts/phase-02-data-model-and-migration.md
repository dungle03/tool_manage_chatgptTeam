# Phase 02: Data Model and Migration

Status: ⬜ Pending
Dependencies: Phase 01

## Objective

Add database support for Personal ChatGPT Accounts without touching Team Workspace tables.

## Requirements

### Functional

- [x] Add `personal_accounts` table/model.
- [x] Store OAuth token values internally.
- [x] Store account metadata for UI cards.
- [x] Store health/check/refresh timestamps.
- [x] Support duplicate email decision flow.
- [x] Track `Need re-login` and other status values.

### Non-Functional

- [x] Tokens must not be returned by list/detail APIs.
- [x] Sensitive fields should be easy to redact in logs.
- [x] Migration/init must be safe for existing SQLite databases.

## Proposed Fields

```text
id
provider
provider_account_id
email
name
plan_type
status
auth_type
access_token
refresh_token
id_token
token_expires_at
refresh_token_updated_at
last_checked_at
last_refreshed_at
next_refresh_at
last_error_code
last_error_message
reauth_required_at
provider_specific_data
is_active
created_at
updated_at
```

## Status Values

```text
unknown
live
die
need_relogin
refreshing
checking
```

## Duplicate Identity Rule

Primary duplicate check should use:

```text
provider + email
```

Secondary duplicate check, if available:

```text
provider + provider_account_id
```

When duplicate exists, backend should return a `duplicate_detected` response instead of silently overwriting.

## Implementation Steps

1. [x] Add `PersonalAccount` model.
2. [x] Add status constants/enums if project style supports it.
3. [x] Add DB initialization/migration logic.
4. [x] Add serializer that excludes tokens by default.
5. [x] Add helper for masked token metadata if ever needed internally.
6. [x] Add basic model tests or DB init regression test.

## Files Created/Modified

- `backend/app/models.py` - add `PersonalAccount` model
- `backend/app/schemas.py` - add public `PersonalAccountOut` response schema
- `backend/app/services/personal_accounts/__init__.py` - service package marker
- `backend/app/services/personal_accounts/serializers.py` - safe serializers and token metadata helpers
- `backend/tests/test_personal_accounts_model.py` - model and serializer regression tests

## Test Criteria

- [x] Existing DB opens successfully.
- [x] New table is created safely.
- [x] Account can be inserted and read back.
- [x] Token fields are present in DB but absent from public response shape.
- [x] Duplicate `provider + email` can be detected.

## Notes

If the project does not use Alembic, follow the existing SQLite initialization style.

---

Next Phase: [Phase 03: OAuth Flow Backend](./phase-03-oauth-flow-backend.md)
