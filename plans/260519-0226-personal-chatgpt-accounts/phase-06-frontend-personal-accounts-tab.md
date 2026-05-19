# Phase 06: Frontend Personal Accounts Tab

Status: ✅ Complete
Dependencies: Phase 05

## Objective

Add a polished Personal Accounts tab to the dashboard.

The user should see account health clearly without seeing token values.

## Requirements

### Functional

- [x] Add tab switcher: Team Workspaces / Personal Accounts.
- [x] Keep Team tab unchanged.
- [x] Add `Add Personal ChatGPT Account` button.
- [x] Display summary stat cards.
- [x] Display personal account cards.
- [x] Support manual `Check Now`, `Refresh`, `Reconnect`, `Delete`.
- [x] Show duplicate account modal.
- [x] Show OAuth success/failure messages.

### Non-Functional

- [x] Never render token values.
- [x] Clear status badges for Live / Die / Need re-login / Unknown.
- [x] Responsive layout.
- [x] Use existing toast/modal patterns where possible.
- [x] UI should feel separate but visually consistent with existing dashboard.

## UI Sections

### Header

```text
Team Workspaces | Personal Accounts
```

### Personal Accounts Toolbar

```text
Title: Personal ChatGPT Accounts
Button: Add Personal ChatGPT Account
```

### Summary Cards

```text
Total Accounts
Live
Need Re-login
Last Auto Refresh
```

### Account Card Fields

```text
Name
Email
Plan
Status
OAuth connected
Last checked
Last refreshed
Next refresh
```

### Account Card Actions

```text
Check Now
Refresh
Reconnect
Delete
```

## Duplicate Modal

Title:

```text
Account already exists
```

Actions:

```text
Overwrite existing
Create new account
Cancel
```

## Implementation Steps

1. [x] Add frontend API client methods.
2. [x] Add personal account TypeScript types.
3. [x] Add dashboard tab state.
4. [x] Add Personal Accounts page/panel component.
5. [x] Add summary cards.
6. [x] Add account card component.
7. [x] Add duplicate modal component.
8. [x] Wire OAuth start action.
9. [x] Wire refresh/check/reconnect/delete actions.
10. [x] Add loading/empty/error states.
11. [x] Add basic responsive polish.

## Files Created/Modified

- `frontend/src/app/page.tsx` - added Team/Personal tab switcher and mounted personal panel.
- `frontend/src/components/personal-accounts-panel.tsx` - personal accounts UI, actions, duplicate modal.
- `frontend/src/lib/api.ts` - personal account API methods.
- `frontend/src/types/personal-accounts.ts` - public frontend types.
- `frontend/src/app/globals.css` - polished responsive styling.

## Empty State

```text
No personal accounts yet.
Add your first Personal ChatGPT account with OAuth.
```

## Error States

- OAuth disabled
- OAuth failed
- Duplicate decision expired
- Refresh failed
- Need re-login
- Delete failed

## Test Criteria

- [x] Team tab still renders as before.
- [x] Personal tab renders empty state.
- [x] Account cards render public account data.
- [x] No token string appears in DOM.
- [x] Duplicate modal can call overwrite/create/cancel actions.
- [x] Manual actions update card status.

## Verification

```text
npm run typecheck
npm test -- --run src/__tests__/dashboard-page.test.tsx src/__tests__/api-client.test.ts
```

Result:

```text
TypeScript passed
2 test files passed, 3 tests passed
```

## Notes

Filter/search can be left for Phase 2 unless implementation is very small.

---

Next Phase: [Phase 07: Integration, Testing, and Hardening](./phase-07-integration-testing-and-hardening.md)
