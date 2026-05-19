# Phase 01: Discovery and Safety Baseline

Status: ⬜ Pending
Dependencies: None

## Objective

Confirm current code boundaries and define safety rules before implementation.

This phase prevents regressions in existing Team Workspace features.

## Requirements

### Functional

- [ ] Identify existing backend app structure and router registration.
- [ ] Identify existing database model/session/migration conventions.
- [ ] Identify frontend dashboard component structure.
- [ ] Confirm where tab navigation should be added.
- [ ] Document token redaction rules.

### Non-Functional

- [ ] Do not change current Team Workspace behavior.
- [ ] Do not modify `get_account_info` team filtering.
- [ ] Do not log access tokens, refresh tokens, or id tokens.
- [ ] Keep Personal Account modules isolated.

## Implementation Steps

1. [x] Inspect backend entrypoint/router registration.
2. [x] Inspect SQLAlchemy models and database initialization.
3. [x] Inspect frontend dashboard page and components.
4. [x] Find existing toast/modal patterns.
5. [x] Create implementation notes for safe file boundaries.
6. [x] Confirm quality commands for backend/frontend.

## Files to Review

- `backend/app/main.py` - router registration
- `backend/app/models.py` - SQLAlchemy models
- `backend/app/db.py` - DB/session setup
- `backend/app/routers/workspaces.py` - existing workspace APIs; avoid risky edits
- `frontend/src/app/page.tsx` - dashboard entrypoint
- `frontend/src/components/` - reusable UI components
- `.brain/brain.json` - project conventions

## Files Created

- `phase-01-notes.md` - discovery notes and safety boundaries

## Test Criteria

- [x] Existing quality commands are known.
- [x] Team Workspace code paths to avoid are documented.
- [x] Personal feature module boundaries are clear.

## Notes

This is a discovery phase. Avoid implementation until Phase 02+.

---

Next Phase: [Phase 02: Data Model and Migration](./phase-02-data-model-and-migration.md)
