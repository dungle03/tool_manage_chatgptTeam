# ChatGPT Workspace Manager

[🇻🇳 Tiếng Việt](./README.md) | [🇺🇸 English](./README.en.md)

**ChatGPT Workspace Manager** is an internal operations dashboard for managing multiple **ChatGPT Team workspaces** and **ChatGPT Personal accounts** from a single interface.

The project combines a **FastAPI backend**, **Next.js frontend**, **SQLite database**, background workers, and real-time updates to support common operational tasks: importing teams, syncing members/invites, monitoring subscription state, refreshing tokens, tracking Personal Plus entitlement data, and keeping local state up to date automatically.

---

## Table of Contents

- [Overview](#overview)
- [What does this project do?](#what-does-this-project-do)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Repository Structure](#repository-structure)
- [Tech Stack](#tech-stack)
- [Quick Start](#quick-start)
- [Environment Variables](#environment-variables)
- [Main API Endpoints](#main-api-endpoints)
- [Database Model](#database-model)
- [Quality Checks](#quality-checks)
- [Operational Notes](#operational-notes)
- [Current Limitations](#current-limitations)
- [Security Notice](#security-notice)

---

## Overview

Operating many ChatGPT Team workspaces or personal ChatGPT accounts manually is slow, repetitive, and prone to stale data.

This project centralizes those workflows into one dashboard:

- track multiple Team workspaces at once
- inspect members, invites, seat usage, and expiry dates
- manage members and invites from one place
- detect members that do not match local policy/state
- manage personal accounts connected through OAuth
- check Personal Plus plan and renewal/expiry data
- automatically sync data in the background
- receive near real-time workspace updates through SSE

The codebase is best suited for:

- internal tools
- local operation or single-instance deployment
- admin dashboards in controlled environments
- workflows that need automated sync/token refresh while still allowing manual operator actions

---

## What does this project do?

At a high level, the project acts as a **control panel** for ChatGPT Team and Personal accounts.

```text
Operator / Admin
        |
        v
Next.js Dashboard
        |
        v
FastAPI Backend
        |
        +--> Local SQLite Database
        +--> Background Sync Worker
        +--> ChatGPT Team/Internal APIs
        +--> Personal Account OAuth / Entitlement Check
        +--> SSE Realtime Events
```

### For ChatGPT Team workspaces

The tool imports workspaces using tokens, stores metadata locally, syncs members/invites from upstream, tracks team expiry/billing dates, refreshes workspace tokens, and provides management actions such as kicking members and creating/resending/cancelling invites.

### For ChatGPT Personal accounts

The tool adds personal accounts through OAuth, stores token metadata, checks health, refreshes tokens, and reads entitlement data to determine plan type and Plus renewal/expiry dates.

### For background sync

The backend runs a background worker to:

- refresh workspace/account tokens when due
- sync stale/hot workspaces according to the scheduler
- sync Personal plan entitlement data in batches
- avoid aggressive upstream calls through batch size and per-account delay settings
- persist sync errors so the dashboard can show operational status

---

## Key Features

### 1. ChatGPT Team workspace management

- Import workspace/team using an `access_token`
- Display all managed workspaces in a unified dashboard
- Track:
  - team name
  - organization ID
  - seat usage
  - member count
  - pending invite count
  - sync status
  - billing/expiry date
  - token health and refresh status
  - last sync / next sync / error state
- View workspace details including members, invites, and unauthorized findings
- Trigger manual sync per workspace
- Trigger manual **Refresh Token** per workspace
- Automatically refresh Team tokens when due
- Manually update a workspace access token when needed
- Rename workspaces in the local dashboard
- Configure unauthorized-member policy per workspace
- Delete workspaces from the local database
- Background scheduler handles stale workspaces and hot workspaces

### 2. Member management

- View members per workspace
- Show member name, email, role, and join time
- Kick members with an explicit confirmation flow
- Persist member snapshots in local SQLite
- Highlight seat overflow or abnormal state cases

### 3. Invite management

- Create new invites by email
- Resend pending invites
- Cancel pending invites
- Track pending invite counts per workspace
- Safely handle duplicate upstream `invite_id` values
- Sync invite state back to the local database

### 4. Unauthorized member detection

- Detect members present upstream but missing from local state/policy
- Support manual review and `auto_kick`
- Persist finding history:
  - first seen
  - last seen
  - status
  - action reason
  - resolved timestamp
- Automatically resolve findings after state reconciliation

### 5. Team token refresh and workspace background sync

This is a core part of the tool, used to keep Team workspaces operational without manually replacing tokens all the time.

- Backend includes a dedicated token-refresh service for Team workspaces
- This flow **does not log in directly inside the dashboard**; it calls a preconfigured tool/token provider that automatically logs into ChatGPT and returns a new access token
- Manual refresh endpoint: `POST /api/workspaces/{id}/refresh-token`
- Manual refresh runs as a background task; the API returns `accepted` or `in_progress`
- Per-workspace locking prevents duplicate refresh jobs
- After the external tool obtains a new token, the backend verifies that the token belongs to the correct workspace/org before marking success
- New token, refresh timestamp, and error state are persisted in the database
- After successful refresh, the backend runs a follow-up workspace sync to update members/invites/summary
- On failure, the backend stores the failure state and publishes an error event to the dashboard
- Auto token refresh cycle runs inside the background worker
- Auto refresh selects due workspaces based on database metadata
- Parallel refresh count and inter-batch delay are limited
- SSE emits:
  - `workspace_token_refreshed`
  - `workspace_token_refresh_failed`
- Scheduler supports hot-window and follow-up sync after important actions
- Retry steps are applied after sync failures
- Workspace sync concurrency is bounded
- SSE pushes workspace updates to the dashboard in near real time

Important Team Refresh Token requirement:

- A working **automatic login/token extraction tool** must already be available in the backend runtime environment
- That tool is responsible for opening/logging into ChatGPT, handling required steps, and exporting a new token in the format expected by the backend
- The backend only orchestrates the refresh, calls that tool, verifies the returned token, saves the database state, and syncs the workspace
- If the token-provider tool fails, is blocked by Cloudflare, logs into the wrong account, or returns an invalid token, the refresh will be marked failed and the dashboard will show the error

### 6. Workspace maintenance tools

- Manually update a workspace access token via dashboard/API
- Rename workspaces locally
- View combined workspace details:
  - workspace summary
  - members
  - invites
  - unauthorized findings
- Configure unauthorized-member mode:
  - manual review
  - auto-kick
- Trust an unauthorized finding when a member is confirmed valid
- Kick directly from an unauthorized finding record
- Global unauthorized findings view across all workspaces

### 7. Personal Accounts dashboard

- Add ChatGPT Personal accounts through OAuth
- Display account status:
  - `live`
  - `die`
  - `need_relogin`
  - `unknown`
- Show email, account name, token expiry, and OAuth status
- Check account health
- Refresh token per account
- Reconnect OAuth when login is required
- Delete personal accounts from the local database

### 8. Personal Plus entitlement tracking

The tool reads personal-account entitlement data and stores/displays:

- `subscription_plan`
- `plan_expires_at`
- `plan_renews_at`
- `last_plan_sync_at`
- `next_plan_sync_at`
- `plan_sync_error`
- `plan_sync_fail_count`

The dashboard account cards display **Plus renews**, while the account management modal shows detailed sync schedule and error metadata.

### 9. Personal Plan Auto Sync

To avoid manually checking many personal accounts one by one, the backend includes a dedicated background sync service for personal accounts.

Mechanism:

- select active accounts with access tokens that are not in `need_relogin`
- sync only accounts that are due according to `next_plan_sync_at`
- limit batch size per background cycle
- delay between accounts to reduce rate-limit/Cloudflare risk
- per-account locking prevents duplicate work between background and manual sync
- if an auth error occurs, try token refresh before marking failure
- on temporary failure, store `plan_sync_error` and retry later

The **Sync Plans** button triggers manual batch sync. The background worker syncs automatically according to schedule.

### 10. Realtime and UI refresh

- Workspace updates are pushed through SSE
- Frontend deduplicates events/toasts to reduce UI noise
- Personal Accounts dashboard has silent polling to pick up background sync changes
- Manual actions reload fresh data after backend commit

### 11. Export utility

A standalone Python export tool is included:

```text
backend/export_workspace_members.py
```

It exports team/member data for auditing or reporting.

---

## Architecture

```text
Frontend
Next.js / React / TypeScript
        |
        | HTTP + SSE
        v
Backend
FastAPI / SQLAlchemy / Pydantic
        |
        +--> SQLite database
        +--> Workspace sync service
        +--> Token refresh service
        +--> Personal account OAuth service
        +--> Personal plan entitlement sync service
        +--> ChatGPT upstream/internal APIs
```

### Core runtime flow

1. The operator uses the Next.js dashboard.
2. The frontend calls FastAPI endpoints.
3. The backend calls upstream ChatGPT APIs when needed.
4. The backend persists state in SQLite.
5. The background worker runs token refresh and sync cycles.
6. Workspace changes are published through SSE.
7. The frontend updates through SSE, manual reloads, or lightweight polling.

### Background worker flow

```text
FastAPI startup
    |
    v
Background loop
    |
    +--> Workspace token refresh cycle
    |       +--> select due workspaces
    |       +--> refresh token
    |       +--> verify token
    |       +--> save success/failure
    |       +--> publish SSE event
    |       +--> follow-up workspace sync
    |
    +--> Workspace sync cycle
    |       +--> stale workspace sync
    |       +--> hot workspace follow-up sync
    |       +--> unauthorized finding reconciliation
    |
    +--> Personal plan sync cycle
    |       +--> select due personal accounts
    |       +--> refresh token on auth failure
    |       +--> sync entitlement/Plus renewal data
    |       +--> save next sync/error state
    |
    v
Sleep according to SYNC_LOOP_INTERVAL_SECONDS
```

---

## Repository Structure

```text
tool_manage_chatgptTeam/
├─ backend/
│  ├─ app/
│  │  ├─ main.py                  # FastAPI app entrypoint
│  │  ├─ db.py                    # Database engine/session/init/migrations
│  │  ├─ models.py                # SQLAlchemy models
│  │  ├─ schemas.py               # Pydantic schemas
│  │  ├─ routers/                 # API routers
│  │  └─ services/                # Business logic services
│  │     ├─ personal_accounts/    # OAuth, health, refresh, sync personal accounts
│  │     ├─ workspace_sync.py     # Workspace background sync orchestration
│  │     └─ workspace_sync_worker.py
│  ├─ tests/                      # Backend tests
│  ├─ export_workspace_members.py # Export utility
│  ├─ requirements.txt
│  └─ pytest.ini
├─ frontend/
│  ├─ src/app/                    # Next.js app routes
│  ├─ src/components/             # React UI components
│  ├─ src/lib/                    # API client, hooks, utilities
│  ├─ src/types/                  # TypeScript types
│  ├─ package.json
│  └─ tsconfig.json
├─ docs/
│  └─ SYNC_RUNBOOK.md             # Sync/realtime debugging runbook
├─ plans/                         # Planning notes
├─ .env                           # Local runtime config
├─ .env.example                   # Example config
├─ start_dashboard.ps1            # Local startup helper
├─ run_backend_tests.ps1          # Backend test helper
├─ run_quality_checks.ps1         # Combined quality checks
├─ README.md
└─ README.en.md
```

---

## Tech Stack

| Layer           | Technology                         |
| --------------- | ---------------------------------- |
| Frontend        | Next.js 14, React 18, TypeScript   |
| Styling         | Vanilla CSS                        |
| Backend         | FastAPI, SQLAlchemy, Pydantic      |
| Database        | SQLite by default                  |
| Realtime        | Server-Sent Events                 |
| Background jobs | Asyncio worker in FastAPI lifespan |
| Backend tests   | pytest                             |
| Frontend tests  | Vitest, Testing Library            |
| Runtime scripts | PowerShell                         |

### Runtime requirements

- **Python**: recommended 3.11+
- **Node.js**: `>= 22.12.0`
- **OS**: currently optimized for a Windows/local PowerShell workflow

---

## Quick Start

### Fast path

From the repository root:

```powershell
.\start_dashboard.ps1
```

The script uses the existing local workflow to run the dashboard/backend according to project configuration.

### Manual backend setup

```powershell
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Run the backend from the `backend/` directory:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Manual frontend setup

Run from the `frontend/` directory:

```powershell
npm install
npm run dev
```

Open the dashboard:

```text
http://localhost:3000
```

---

## Environment Variables

The project currently uses the root `.env` file for local runtime. Some deployments may also use `backend/.env` or `frontend/.env.local`, depending on how the startup script is run.

### Core backend

| Variable                                    | Default                                   | Purpose                                          |
| ------------------------------------------- | ----------------------------------------- | ------------------------------------------------ |
| `DATABASE_URL`                              | `backend/workspace_manager.db` when unset | Database connection string                       |
| `ADMIN_TOKEN`                               | empty                                     | Protects admin endpoints                         |
| `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC` | empty                                     | Disables background sync for tests/isolated runs |

### Workspace sync

| Variable                       | Default      | Purpose                                  |
| ------------------------------ | ------------ | ---------------------------------------- |
| `SYNC_LOOP_INTERVAL_SECONDS`   | `5`          | Main background loop interval            |
| `SYNC_STALE_MINUTES`           | `5`          | Workspace stale threshold                |
| `SYNC_PENDING_INVITE_SECONDS`  | `15`         | Faster sync when pending invites exist   |
| `SYNC_BASELINE_MINUTES`        | `5`          | Baseline background refresh interval     |
| `SYNC_HOT_WINDOW_SECONDS`      | `180`        | Duration a workspace stays in hot state  |
| `SYNC_FOLLOWUP_STEPS`          | `5,15,30,60` | Follow-up sync checkpoints after actions |
| `SYNC_ERROR_RETRY_STEPS`       | `10,30,60`   | Retry checkpoints after sync errors      |
| `SYNC_MAX_PARALLEL_WORKSPACES` | `2`          | Maximum parallel workspace syncs         |

### Personal account OAuth

| Variable                            | Purpose                        |
| ----------------------------------- | ------------------------------ |
| `ENABLE_EXPERIMENTAL_CHATGPT_OAUTH` | Enables Personal Account OAuth |
| `CHATGPT_OAUTH_CLIENT_ID`           | OAuth client ID                |
| `CHATGPT_OAUTH_AUTH_URL`            | OAuth authorization URL        |
| `CHATGPT_OAUTH_TOKEN_URL`           | OAuth token URL                |
| `CHATGPT_OAUTH_REDIRECT_URI`        | Local redirect URI             |
| `CHATGPT_OAUTH_SCOPE`               | OAuth scopes                   |

### Personal Plan Auto Sync

| Variable                           | Default | Purpose                                                |
| ---------------------------------- | ------- | ------------------------------------------------------ |
| `PERSONAL_PLAN_SYNC_STALE_HOURS`   | `6`     | How long before an account should sync plan data again |
| `PERSONAL_PLAN_SYNC_BATCH_SIZE`    | `5`     | Maximum personal accounts synced per background cycle  |
| `PERSONAL_PLAN_SYNC_DELAY_SECONDS` | `2`     | Delay between accounts in a sync batch                 |
| `PERSONAL_PLAN_SYNC_RETRY_MINUTES` | `45`    | Retry delay after temporary failure                    |

Recommended configuration for many personal accounts:

```env
SYNC_LOOP_INTERVAL_SECONDS=30
PERSONAL_PLAN_SYNC_STALE_HOURS=6
PERSONAL_PLAN_SYNC_BATCH_SIZE=3
PERSONAL_PLAN_SYNC_DELAY_SECONDS=5
PERSONAL_PLAN_SYNC_RETRY_MINUTES=45
```

### Frontend

| Variable                  | Purpose                             |
| ------------------------- | ----------------------------------- |
| `NEXT_PUBLIC_ADMIN_TOKEN` | Token sent from frontend to backend |

---

## Main API Endpoints

### Workspace APIs

| Method   | Endpoint                                                       | Description                                              |
| -------- | -------------------------------------------------------------- | -------------------------------------------------------- |
| `GET`    | `/api/workspaces`                                              | List managed workspaces                                  |
| `POST`   | `/api/teams/import`                                            | Import a workspace/team from token                       |
| `GET`    | `/api/workspaces/{id}/details`                                 | Get summary, members, invites, and unauthorized findings |
| `GET`    | `/api/workspaces/{id}/members`                                 | List workspace members                                   |
| `POST`   | `/api/workspaces/{id}/sync`                                    | Trigger immediate workspace sync                         |
| `POST`   | `/api/workspaces/{id}/refresh-token`                           | Trigger workspace token refresh as a background task     |
| `PATCH`  | `/api/workspaces/{id}/token`                                   | Manually update workspace access token                   |
| `PATCH`  | `/api/workspaces/{id}/name`                                    | Rename workspace locally                                 |
| `PATCH`  | `/api/workspaces/{id}/unauthorized-policy`                     | Change unauthorized-member handling mode                 |
| `GET`    | `/api/workspaces/{id}/unauthorized-members`                    | List unauthorized findings for one workspace             |
| `POST`   | `/api/workspaces/{id}/unauthorized-members/{finding_id}/trust` | Trust an unauthorized finding                            |
| `POST`   | `/api/workspaces/{id}/unauthorized-members/{finding_id}/kick`  | Kick a member from an unauthorized finding               |
| `GET`    | `/api/unauthorized-findings`                                   | List all unauthorized findings                           |
| `DELETE` | `/api/workspaces/{id}`                                         | Delete workspace from local database                     |
| `GET`    | `/api/events/workspaces`                                       | Open workspace SSE stream                                |

### Member / Invite APIs

| Method   | Endpoint                  | Description                    |
| -------- | ------------------------- | ------------------------------ |
| `DELETE` | `/api/member`             | Kick a member from a workspace |
| `POST`   | `/api/invite`             | Create an invite               |
| `POST`   | `/api/resend-invite`      | Resend a pending invite        |
| `DELETE` | `/api/cancel-invite`      | Cancel a pending invite        |
| `GET`    | `/api/invites?org_id=...` | List invites for a workspace   |

### Personal Account APIs

| Method   | Endpoint                                         | Description                                 |
| -------- | ------------------------------------------------ | ------------------------------------------- |
| `GET`    | `/api/personal-accounts`                         | List personal accounts                      |
| `GET`    | `/api/personal-accounts/{id}`                    | Get personal account details                |
| `POST`   | `/api/personal-accounts/{id}/check`              | Check health and sync plan for one account  |
| `POST`   | `/api/personal-accounts/{id}/refresh`            | Refresh token for one account               |
| `POST`   | `/api/personal-accounts/{id}/reconnect/start`    | Create OAuth reconnect URL                  |
| `POST`   | `/api/personal-accounts/oauth/start`             | Start Personal Account OAuth                |
| `GET`    | `/api/personal-accounts/oauth/callback`          | Complete OAuth through redirect callback    |
| `POST`   | `/api/personal-accounts/oauth/callback-url`      | Complete OAuth from copied callback URL     |
| `POST`   | `/api/personal-accounts/oauth/resolve-duplicate` | Resolve duplicate OAuth account import      |
| `POST`   | `/api/personal-accounts/sync`                    | Batch sync Personal plan entitlement data   |
| `DELETE` | `/api/personal-accounts/{id}`                    | Delete personal account from local database |

Manual Personal plan sync example:

```text
POST /api/personal-accounts/sync?limit=10&force=true
```

---

## Database Model

### `workspaces`

Stores each ChatGPT Team workspace and its operational state:

- team name
- org/account ID
- access token
- expiry/billing-cycle date
- sync/scheduler metadata
- token refresh status
- error state

### `members`

Stores member snapshots per workspace:

- remote member ID
- name
- email
- role
- join time

### `invites`

Stores invite state:

- email
- invite ID
- pending status
- whether the invite was created by the tool
- local/upstream sync state

### `unauthorized_findings`

Stores unauthorized-member detection and remediation history:

- remote ID
- email
- role
- current status
- action reason
- first seen / last seen / resolved timestamps

### `personal_accounts`

Stores ChatGPT Personal accounts added to the tool:

- email/name/avatar
- OAuth token and refresh-token metadata
- token expiry/refresh schedule
- account status
- subscription plan
- Plus renew/expire date
- plan sync schedule
- plan sync error/fail count

---

## Exporting Team and Member Data

Standalone export tool:

```text
backend/export_workspace_members.py
```

Example from the `backend/` directory:

```powershell
python export_workspace_members.py --format csv --output exports/team_members_export.csv --include-empty-teams
```

Main exported fields:

- `team_name`
- `team_id`
- `team_expires_at`
- `member_name`
- `member_email`
- `member_role`
- `member_joined_at`

---

## Quality Checks

### Combined command

From the repository root:

```powershell
.\run_quality_checks.ps1
```

The script runs:

1. Backend lint with Ruff.
2. Backend regression tests with pytest.
3. Frontend TypeScript check.
4. Frontend tests with Vitest.

Skip individual sections when needed:

```powershell
.\run_quality_checks.ps1 -SkipBackend
.\run_quality_checks.ps1 -SkipFrontend
```

### Backend

Recommended:

```powershell
.\run_backend_tests.ps1
```

Or from the `backend/` directory:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Python lint from the repository root:

```powershell
.\backend\venv\Scripts\python.exe -m ruff check backend
```

### Frontend

Run from the `frontend/` directory:

```powershell
npm run typecheck
npm test
```

Or use the combined frontend script:

```powershell
npm run verify
```

Production build when needed:

```powershell
npm run build
```

---

## Operational Notes

- Local SQLite defaults to a database under `backend/` unless `DATABASE_URL` overrides it.
- If you change the database file, restore a backup, or change `DATABASE_URL`, restart the backend.
- Workspace deletion currently removes the workspace from the local management database; review separately before treating it as a destructive upstream action.
- Member deletion calls upstream first, then removes the local row.
- Invite creation handles duplicate upstream `invite_id` values idempotently.
- Team Refresh Token has both manual and auto flows:
  - manual through the `refresh-token` button/API
  - auto through the background token refresh cycle
  - both require a preconfigured automatic login/token-provider tool
  - the backend does not replace that browser-login tool; it only calls the tool, receives the token, verifies it, and saves the result
  - locking prevents duplicate refresh jobs
  - new tokens are verified before marking success
  - follow-up workspace sync runs after successful refresh
- If Team Refresh Token is already running, another request receives `in_progress` instead of creating a duplicate task.
- Manual token update should only be used when the new token is confirmed to belong to the correct workspace/org.
- Personal Plan Sync does not sync every account every cycle; it only syncs accounts due by `next_plan_sync_at`.
- The `Reload` button on Personal Accounts only reloads the database state; it does not call ChatGPT upstream.
- `Check Now` syncs one personal account.
- `Sync Plans` batch-syncs multiple personal accounts immediately.
- Background Personal Plan Sync uses batch/delay settings to reduce Cloudflare/rate-limit risk.
- For realtime/background sync debugging, start with:

```text
docs/SYNC_RUNBOOK.md
```

---

## Current Limitations

- SSE is currently best suited for single-instance deployment.
- SQLite is convenient for local/internal use; PostgreSQL is a better fit for larger deployments or multiple operators.
- The project depends on ChatGPT internal/team APIs; backend updates may be required when upstream contracts change.
- Personal entitlement endpoints are internal APIs, so defensive parsing may need updates if upstream payloads change.
- Multi-instance realtime delivery requires shared event infrastructure such as Redis/pub-sub.
- The tool should run in a controlled environment because it stores token/account metadata.

---

## Security Notice

This repository is intended for internal and controlled operational environments.

Before production use or public release, review:

- authentication and admin-token handling
- secret storage
- token encryption/rotation
- access control
- audit logging
- database backup/restore
- internal compliance policies
- upstream/internal API dependency risk

Do not commit `.env` files, real tokens, real databases, or exports containing user data to a public repository.

---

## License

Add your preferred license before publishing the repository.
