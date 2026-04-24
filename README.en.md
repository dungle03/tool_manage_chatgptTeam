# ChatGPT Workspace Manager

[🇻🇳 Tiếng Việt](./README.md) | [🇺🇸 English](./README.en.md)

A full-stack operations dashboard for managing multiple ChatGPT Team workspaces from one place.

It combines a **Next.js frontend** and a **FastAPI backend** to help operators import workspaces, inspect members and invites, run management actions, and keep the dashboard fresh through **background sync** and **real-time SSE updates**.

---

## Overview

Managing multiple ChatGPT Team workspaces manually is slow, repetitive, and hard to audit. This project centralizes the operational workflow into a single dashboard so you can:

- import and track multiple workspaces
- inspect members and pending invites quickly
- kick members and manage pending invites
- trigger manual syncs when needed
- receive near real-time updates without reloading the page
- monitor unauthorized members and auto-kick behavior
- observe token refresh lifecycle and workspace sync health

The current codebase is well suited for:

- internal tooling
- single-instance deployments
- operator dashboards
- local development and controlled environments

---

## Key Features

### Workspace management

- Import a workspace using an `access_token`
- View all managed workspaces in one dashboard
- Track team name, organization ID, seat usage, sync status, and expiration date
- Remove a workspace from the local management database
- Trigger manual sync per workspace
- Run background scheduling for stale and hot workspaces

### Member management

- View members per workspace
- Show member name, email, role, and join date
- Kick a member with explicit confirmation flow
- Persist member state in the local database
- Highlight seat overflow cases in the dashboard

### Invite management

- Create new invites by email
- Resend pending invites
- Cancel pending invites
- Track pending invite counts per workspace
- Handle duplicate upstream invite IDs safely

### Unauthorized member enforcement

- Detect members present remotely but missing from the local whitelist
- Support `auto_kick` and manual review flows
- Persist unauthorized findings with status history
- Automatically resolve findings after successful removal or state reconciliation

### Token refresh and realtime sync

- Background worker starts with FastAPI lifespan
- Smart scheduling with hot-window and follow-up sync behavior
- Token refresh lifecycle persists status in the database
- SSE pushes workspace updates to the dashboard in near real time
- Frontend deduplicates events and toasts to reduce UI noise

### Export utility

- Includes a standalone Python export tool for extracting team/member data from the local database:
  - `backend/export_workspace_members.py`

---

## Architecture

```text
Frontend (Next.js / React / TypeScript)
        |
        v
Backend API (FastAPI)
        |
        +--> SQLAlchemy ORM
        +--> SQLite database (default)
        +--> Background sync scheduler
        +--> SSE event stream
        +--> ChatGPT internal/team APIs
```

### Core runtime flow

1. The frontend calls backend APIs for workspace, member, and invite actions.
2. The backend persists workspace state in the local database.
3. A background scheduler continuously checks which workspaces need sync or token refresh.
4. The backend emits SSE events when workspace state changes.
5. The frontend listens to SSE and updates cards, banners, and toast notifications.

---

## Repository Structure

```text
tool_manage_chatgptTeam/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ db.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  ├─ routers/
│  │  └─ services/
│  ├─ tests/
│  ├─ export_workspace_members.py
│  ├─ seed.py
│  ├─ pytest.ini
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/
│  ├─ src/components/
│  ├─ src/lib/
│  ├─ src/types/
│  └─ package.json
├─ docs/
│  ├─ PROJECT_REVIEW_20260312.md
│  ├─ PROJECT_REVIEW_20260407.md
│  └─ SYNC_RUNBOOK.md
├─ run_backend_tests.ps1
├─ start_dashboard.ps1
└─ README.md
```

---

## Tech Stack

| Layer          | Technology                       |
| -------------- | -------------------------------- |
| Frontend       | Next.js 14, React 18, TypeScript |
| Styling        | Vanilla CSS                      |
| Backend        | FastAPI, SQLAlchemy, Pydantic    |
| Database       | SQLite by default                |
| Realtime       | Server-Sent Events (SSE)         |
| Backend tests  | pytest                           |
| Frontend tests | Vitest, Testing Library          |

### Runtime requirements

- **Python**: recommended 3.11+
- **Node.js**: `>= 22.12.0`

---

## Quick Start

### 1. Backend setup

```powershell
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Create `backend/.env` from `backend/.env.example` if needed.

Run the backend from the `backend/` directory:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Frontend setup

Run the frontend from the `frontend/` directory:

```powershell
npm install
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

### Backend (`backend/.env`)

| Variable                                    | Default                                                                                                                                          | Purpose                                          |
| ------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------------------------------------------------ |
| `DATABASE_URL`                              | `sqlite:///C:/.../tool_manage_chatgptTeam/backend/workspace_manager.db` _(when unset, the app anchors itself to `backend/workspace_manager.db`)_ | Backend database connection string               |
| `SYNC_LOOP_INTERVAL_SECONDS`                | `5`                                                                                                                                              | Main background loop interval                    |
| `SYNC_STALE_MINUTES`                        | `5`                                                                                                                                              | Threshold to mark a workspace stale              |
| `SYNC_PENDING_INVITE_SECONDS`               | `15`                                                                                                                                             | Faster polling when pending invites exist        |
| `SYNC_BASELINE_MINUTES`                     | `5`                                                                                                                                              | Baseline background refresh interval             |
| `SYNC_HOT_WINDOW_SECONDS`                   | `180`                                                                                                                                            | Duration a workspace stays in hot state          |
| `SYNC_FOLLOWUP_STEPS`                       | `5,15,30,60`                                                                                                                                     | Follow-up sync checkpoints after key actions     |
| `SYNC_ERROR_RETRY_STEPS`                    | `10,30,60`                                                                                                                                       | Retry checkpoints after sync failure             |
| `SYNC_MAX_PARALLEL_WORKSPACES`              | `2`                                                                                                                                              | Maximum parallel workspace sync count            |
| `ADMIN_TOKEN`                               | unset                                                                                                                                            | Protects admin endpoints                         |
| `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC` | unset                                                                                                                                            | Disables background sync for isolated runs/tests |

> Note: the canonical local SQLite file is now `backend/workspace_manager.db`.
> Avoid leaving an extra `workspace_manager.db` at the repository root and assuming the app will pick the right one automatically, because it can cause silent data drift between runs.

### Frontend (`frontend/.env.local`)

| Variable                  | Purpose                             |
| ------------------------- | ----------------------------------- |
| `NEXT_PUBLIC_ADMIN_TOKEN` | Token sent from frontend to backend |

---

## Main API Endpoints

| Method   | Endpoint                             | Description                                |
| -------- | ------------------------------------ | ------------------------------------------ |
| `GET`    | `/api/workspaces`                    | List managed workspaces                    |
| `POST`   | `/api/teams/import`                  | Import a workspace/team from token         |
| `POST`   | `/api/workspaces/{id}/sync`          | Trigger immediate workspace sync           |
| `POST`   | `/api/workspaces/{id}/refresh-token` | Trigger token refresh                      |
| `DELETE` | `/api/workspaces/{id}`               | Delete a workspace from the local database |
| `GET`    | `/api/workspaces/{id}/members`       | List members for a workspace               |
| `DELETE` | `/api/member`                        | Kick a member                              |
| `POST`   | `/api/invite`                        | Create an invite                           |
| `POST`   | `/api/resend-invite`                 | Resend a pending invite                    |
| `DELETE` | `/api/cancel-invite`                 | Cancel a pending invite                    |
| `GET`    | `/api/invites?org_id=...`            | List invites for a workspace               |
| `GET`    | `/api/events/workspaces`             | Open the SSE stream                        |

---

## Database Model Summary

### `workspaces`

Stores each imported workspace and its operational state:

- team name
- org/account IDs
- access token
- expiration date
- sync health and scheduling metadata
- token refresh status

### `members`

Stores the latest member snapshot per workspace:

- remote member ID
- name
- email
- role
- join time

### `invites`

Stores pending invite state:

- email
- invite ID
- pending status
- whether the invite was created by this tool

### `unauthorized_findings`

Stores unauthorized-member detection and remediation history:

- remote ID
- email
- role
- current finding status
- action reason
- timestamps for first seen, last seen, and resolution

---

## Exporting Team and Member Data

A standalone export tool is included:

- `backend/export_workspace_members.py`

Example usage:

```powershell
python export_workspace_members.py --format csv --output exports/team_members_export.csv --include-empty-teams
```

Exported fields:

- `team_name`
- `team_id`
- `team_expires_at`
- `member_name`
- `member_email`
- `member_role`
- `member_joined_at`

---

## Quality Checks

### One-command local verification

Recommended from the repository root:

```powershell
.\run_quality_checks.ps1
```

This script runs:

1. Backend lint with Ruff.
2. Backend regression tests with pytest from `backend/venv`.
3. Frontend TypeScript check.
4. Frontend tests with Vitest.

You can skip either side when needed:

```powershell
.\run_quality_checks.ps1 -SkipBackend
.\run_quality_checks.ps1 -SkipFrontend
```

### Backend

Recommended:

```powershell
.\run_backend_tests.ps1
```

Alternative from the `backend/` directory:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Python lint from the repository root:

```powershell
.\backend\venv\Scripts\python.exe -m ruff check backend
```

> Avoid running `python -m pytest backend/tests` from the repository root. It can run in the wrong context and appear to hang.

### Frontend

Run from the `frontend/` directory:

```powershell
npm run typecheck
npm test
```

Or use the combined script:

```powershell
npm run verify
```

Production build check:

```powershell
npm run build
```

---

## Operational Notes

- Member deletion removes the member upstream first, then deletes the local database row.
- Workspace deletion removes the workspace and its related local data from the database.
- The current workspace delete flow is local-management deletion; review upstream behavior separately before treating it as a remote destructive action.
- Unauthorized-member auto-kick relies on remote member identifiers from upstream payloads.
- Invite creation is idempotent against duplicate upstream `invite_id` values.
- The default backend-local SQLite path is always anchored to `backend/workspace_manager.db` unless `DATABASE_URL` overrides it.
- If you change `DATABASE_URL`, swap SQLite files, or restore a backup, restart the backend so an older process does not keep stale runtime state.

For realtime and background sync debugging, start with:

- `docs/SYNC_RUNBOOK.md`

---

## Current Limitations

- SSE delivery is designed primarily for **single-instance deployment**.
- SQLite is convenient for local/internal use, but PostgreSQL is a better choice for larger deployments.
- The project depends on ChatGPT internal/team APIs, so upstream contract changes may require backend updates.
- Multi-instance realtime delivery would require shared event infrastructure such as Redis/pub-sub.

---

## Security Notice

This repository is intended for controlled environments and internal operational workflows.

Before using it in production, review:

- authentication and admin-token handling
- secret storage practices
- access control requirements
- compliance and organizational policies
- upstream API usage risk

---

## License

Add your preferred license here before publishing the repository.
