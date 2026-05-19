# Phase 07: Integration, Testing, and Hardening

Status: ⬜ Pending
Dependencies: Phase 06

## Objective

Validate the full Personal Accounts flow and protect existing Team Workspace behavior.

## Requirements

### Functional

- [ ] Full OAuth add flow works locally.
- [ ] Duplicate account decision works.
- [ ] Manual refresh/check actions work.
- [ ] Reconnect works for `Need re-login` accounts.
- [ ] Delete works safely.
- [ ] Existing Team Workspace dashboard still works.

### Non-Functional

- [ ] No tokens in frontend DOM.
- [ ] No tokens in backend logs.
- [ ] No tokens in API responses.
- [ ] Refresh race condition is handled.
- [ ] Errors are readable.

## Test Matrix

| Scenario                  | Expected Result                       |
| ------------------------- | ------------------------------------- |
| Add new account via OAuth | Account card appears                  |
| Add duplicate email       | Duplicate modal appears               |
| Choose overwrite          | Existing card updates                 |
| Choose create new         | New card is added                     |
| Choose cancel             | No account is changed                 |
| Refresh success           | Status becomes/remains Live           |
| Refresh invalid_grant     | Status becomes Need re-login          |
| Check success             | Last checked updates                  |
| Delete account            | Card disappears                       |
| Team tab opened           | Existing workspace behavior unchanged |

## Security Checks

- [ ] Search frontend bundle/source for accidental token rendering.
- [ ] Inspect backend response schemas for token fields.
- [ ] Inspect logging calls for token-bearing objects.
- [ ] Ensure OAuth callback errors do not include raw token response.

## Quality Commands

Use project conventions from `.brain/brain.json`:

```powershell
.\run_quality_checks.ps1
```

Backend targeted checks:

```powershell
.\backend\venv\Scripts\python.exe -m ruff check backend/app backend/export_workspace_members.py
```

Frontend targeted checks:

```powershell
npm run verify
```

## Implementation Steps

1. [ ] Add backend unit tests for refresh manager.
2. [ ] Add backend endpoint tests for public response redaction.
3. [ ] Add frontend render tests if project test structure supports it.
4. [ ] Run manual OAuth flow locally.
5. [ ] Run duplicate flow manually.
6. [ ] Run Team tab smoke test.
7. [ ] Run quality commands.
8. [ ] Document known limitations.

## Files to Create/Modify

- `backend/tests/` - refresh/API tests
- `frontend/src/**/*.test.*` - frontend tests if current project uses them
- `docs/specs/personal_chatgpt_accounts_spec.md` - final detailed spec if not already created
- `.env.example` - OAuth config examples without secrets if appropriate

## Release Criteria

- [ ] MVP behavior is complete.
- [ ] Team tab has no regression.
- [ ] Token leak checks pass.
- [ ] Refresh unrecoverable errors are safe.
- [ ] User can recover through Reconnect.

## Notes

Because Codex OAuth is experimental, final UI should communicate failures clearly without implying the user did something wrong.

---

Next Step: `/design` recommended before coding detailed DB/API contracts.
