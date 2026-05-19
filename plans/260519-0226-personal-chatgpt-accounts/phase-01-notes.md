# Phase 01 Notes: Discovery and Safety Baseline

Created: 2026-05-19 02:34 +07:00
Feature: Personal ChatGPT Accounts OAuth

## 1. Backend structure

### App entrypoint

File: `backend/app/main.py`

Current routers:

```python
from app.routers import events, invites, members, workspaces

app.include_router(workspaces.router)
app.include_router(members.router)
app.include_router(invites.router)
app.include_router(events.router)
```

Safe extension point:

```python
from app.routers import events, invites, members, personal_accounts, workspaces
app.include_router(personal_accounts.router)
```

### Existing router pattern

File: `backend/app/routers/workspaces.py`

Boundary rule:

- Do not mix Personal Account endpoints into `workspaces.py`.
- Create `backend/app/routers/personal_accounts.py`.
- Keep `/api/workspaces` contract unchanged.

## 2. Database conventions

### Models

File: `backend/app/models.py`

Current models:

- `Workspace`
- `Member`
- `Invite`
- `UnauthorizedFinding`

Project uses SQLAlchemy 2 style:

```python
class Base(DeclarativeBase):
    pass

field: Mapped[type] = mapped_column(...)
```

Safe extension point:

- Add `PersonalAccount(Base)` at end of `models.py`.
- Use table name `personal_accounts`.
- Add indexes with `Index(...)` in `__table_args__`.

### DB init and migration

File: `backend/app/db.py`

Current behavior:

```python
Base.metadata.create_all(bind=engine)
_migrate_add_missing_columns()
```

Migration style:

- `create_all()` creates new tables.
- `_migrate_add_missing_columns()` adds columns to old SQLite DBs.
- Existing DB file default: `backend/workspace_manager.db`.

Safe extension point:

- Let `create_all()` create `personal_accounts` table.
- Add future columns through `_migrate_add_missing_columns()` if needed.
- Do not rename existing tables/columns.

Correction from phase file:

- The real DB file is `backend/app/db.py`, not `backend/app/database.py`.

## 3. Backend schema/API conventions

File: `backend/app/schemas.py`

Current style:

- Pydantic `BaseModel` classes live in one shared `schemas.py`.
- Existing response models use snake_case fields.

Safe extension point:

- Add `PersonalAccountOut` and action-result schemas to `schemas.py` for consistency.
- If the file grows too much later, split into `schemas/personal_accounts.py` in a later refactor only after asking.

## 4. Frontend dashboard structure

### Dashboard entry

File: `frontend/src/app/page.tsx`

Current structure:

- Single dashboard page.
- State-heavy component.
- Imports reusable components from `frontend/src/components`.
- Uses toast hook `useDashboardToasts()`.
- Main render starts around the dashboard header.

Safe tab insertion point:

- Add a dashboard-level tab state near existing UI state:

```ts
const [activeDashboardTab, setActiveDashboardTab] = useState<
  "teams" | "personal"
>("teams");
```

- Keep all current Team UI under `activeDashboardTab === "teams"`.
- Render new `PersonalAccountsPanel` under `activeDashboardTab === "personal"`.
- Keep existing `ImportDialog`, workspace modals, and workspace effects unchanged.

### Existing frontend API client

File: `frontend/src/lib/api.ts`

Current pattern:

- Central `requestJson()` helper.
- GET cache and in-flight de-dup exist.
- Mutations invalidate GET cache.
- Auth header supports `NEXT_PUBLIC_ADMIN_TOKEN`.

Safe extension point:

- Add personal account client functions here.
- Add personal account types in `frontend/src/types/api.ts` or a dedicated `frontend/src/types/personal-accounts.ts`.
- Avoid returning/rendering token fields.

## 5. Toast/modal patterns

### Toast

Files:

- `frontend/src/lib/use-dashboard-toasts.ts`
- `frontend/src/components/toast-stack.tsx`

Pattern:

```ts
showToast(title, message, tone, dedupeKey);
```

Use this for Personal Accounts action messages.

### Modal/dialog

Existing examples:

- `frontend/src/components/import-dialog.tsx`
- `frontend/src/components/rename-workspace-dialog.tsx`
- `frontend/src/components/update-token-dialog.tsx`

Pattern:

- Overlay div.
- Inner dialog stops click propagation.
- Local `loading` and `error` state.
- Existing classes: `confirm-overlay`, `import-dialog`, `btn`, `btn-primary`, `btn-ghost`.

Use this pattern for duplicate-account modal.

## 6. Safety boundaries

Do not modify these behaviors in Phase 02+ unless explicitly required:

- `ChatGPTService.get_account_info` team filtering.
- Existing `/api/workspaces` endpoints.
- Existing workspace sync behavior.
- Existing Team Import dialog behavior.
- Existing workspace token refresh flow.

Personal Accounts must be added as separate modules:

```text
backend/app/routers/personal_accounts.py
backend/app/services/personal_accounts/*
frontend/src/components/personal-accounts-panel.tsx
frontend/src/components/personal-account-card.tsx
frontend/src/components/personal-account-duplicate-modal.tsx
```

## 7. Token redaction rules

Never return these fields from public APIs:

```text
access_token
refresh_token
id_token
```

Never log raw objects containing:

```text
access_token
refresh_token
id_token
authorization
bearer
```

Frontend must never:

- Render token values.
- Store token values in React state.
- Put token values in query params.
- Show token values in toast/error text.

Backend should expose only safe booleans/timestamps:

```text
oauth_connected
requires_relogin
token_expires_at
last_checked_at
last_refreshed_at
next_refresh_at
last_error_code
last_error_message
```

## 8. Quality commands

Full quality gate:

```powershell
.\run_quality_checks.ps1
```

Backend only:

```powershell
.\run_quality_checks.ps1 -SkipFrontend
```

Frontend only:

```powershell
.\run_quality_checks.ps1 -SkipBackend
```

Backend targeted:

```powershell
.\backend\venv\Scripts\python.exe -m ruff check backend/app backend/export_workspace_members.py
```

Backend tests:

```powershell
.\backend\venv\Scripts\python.exe -m pytest
```

Frontend verify:

```powershell
npm run verify
```

Run frontend command from:

```text
frontend/
```

## 9. Phase 01 result

All discovery items complete.

Ready for Phase 02:

```text
/code phase-02
```
