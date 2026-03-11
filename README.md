# ChatGPT Workspace Manager

A unified dashboard for managing multiple **ChatGPT Team** workspaces from one place.

You can import teams, inspect members, manage invites, remove members, manually sync data, and receive near-realtime dashboard updates through **SSE + Realtime Sync V2**.

---

## Features

### Workspace operations
- Import a team with `access_token` or `session_token`
- View all workspaces in one dashboard
- Delete a workspace from local management
- See team seat usage, sync state, and expiration date

### Member management
- View members per workspace
- Display member join date in `dd/mm/yyyy`
- Remove members with confirmation flow
- Surface role and over-limit member states in the UI

### Invite management
- Invite a new member by email
- Resend a pending invite
- Cancel a pending invite
- Track pending invites per workspace

### Realtime Sync V2
- Background sync worker started with FastAPI lifespan
- Smart scheduler using hot queue + follow-up sync windows
- Priority-based sync behavior for hot workspaces and pending invites
- Server-Sent Events for dashboard updates
- Frontend event handling for:
  - `sync_started`
  - `workspace_updated`
  - `sync_failed`
  - `workspace_scheduled`
  - `heartbeat`

### UI highlights
- Dark premium dashboard UI
- Animated SVG chevron for workspace expand/collapse
- Team expiration date shown below workspace name
- Sync status, hot state, and sync reason surfaced in workspace cards

---

## Architecture

```text
Frontend (Next.js) -> Backend API (FastAPI) -> ChatGPT Internal API
                         |
                         +-> SQLite / PostgreSQL
                         |
                         +-> Background Sync Worker
                         |
                         +-> SSE Event Stream
```

### Main project structure

```text
tool_manage_chatgptTeam/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ db.py
│  │  ├─ models.py
│  │  ├─ routers/
│  │  ├─ schemas.py
│  │  └─ services/
│  ├─ tests/
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/
│  ├─ src/components/
│  ├─ src/lib/
│  └─ src/types/
├─ docs/
│  ├─ DESIGN.md
│  └─ PROJECT_REVIEW_20260312.md
└─ README.md
```

---

## Tech Stack

| Layer | Technology |
|------|------------|
| Frontend | Next.js 14, React 18, TypeScript |
| Styling | Vanilla CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite (dev), PostgreSQL-ready |
| Realtime | Server-Sent Events (SSE) |
| Backend tests | pytest |
| Frontend tests | Vitest, Testing Library |

---

## Quick Start

## 1) Backend

```bash
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Create `backend/.env` from `backend/.env.example` and adjust values if needed.

Run the API:

```bash
uvicorn app.main:app --reload --port 8000
```

> Run this command from the `backend/` directory.

## 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Open: [http://localhost:3000](http://localhost:3000)

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|---------|---------|---------|
| `DATABASE_URL` | `sqlite:///./workspace_manager.db` | Database connection string |
| `SYNC_LOOP_INTERVAL_SECONDS` | `5` | Background loop interval |
| `SYNC_STALE_MINUTES` | `5` | Legacy stale threshold |
| `SYNC_PENDING_INVITE_SECONDS` | `15` | Faster checks for pending invites |
| `SYNC_BASELINE_MINUTES` | `5` | Baseline refresh cadence |
| `SYNC_HOT_WINDOW_SECONDS` | `180` | How long a workspace stays hot |
| `SYNC_FOLLOWUP_STEPS` | `5,15,30,60` | Follow-up sync schedule after key actions |
| `SYNC_ERROR_RETRY_STEPS` | `10,30,60` | Retry schedule after sync failure |
| `SYNC_MAX_PARALLEL_WORKSPACES` | `2` | Max concurrent workspace sync jobs |
| `ADMIN_TOKEN` | _unset_ | Protect backend API |

### Frontend (`frontend/.env.local`)

| Variable | Purpose |
|---------|---------|
| `NEXT_PUBLIC_ADMIN_TOKEN` | Sends auth token to the backend from the dashboard |

---

## API Overview

| Method | Endpoint | Description |
|------|----------|-------------|
| `GET` | `/api/workspaces` | List all managed workspaces |
| `POST` | `/api/teams/import` | Import one or more teams from token data |
| `GET` | `/api/workspaces/{id}/members` | List workspace members |
| `GET` | `/api/workspaces/{id}/sync` | Trigger a manual sync |
| `DELETE` | `/api/workspaces/{id}` | Delete a managed workspace |
| `POST` | `/api/invite` | Invite a member |
| `GET` | `/api/invites?org_id=...` | List pending invites |
| `POST` | `/api/resend-invite` | Resend an invite |
| `DELETE` | `/api/cancel-invite` | Cancel an invite |
| `DELETE` | `/api/member` | Remove a member |
| `GET` | `/api/events/workspaces` | Open SSE stream for workspace events |

---

## Running Tests

### Frontend

```bash
cd frontend
npm test
npm run build
```

### Backend

```bash
cd backend
python -m pytest backend/tests
```

> Note: there has been a recent case where the full backend pytest run stayed active much longer than expected. If that happens again, inspect the hanging test or background worker lifecycle before deploying.

---

## Authentication

When `ADMIN_TOKEN` is configured on the backend, all protected endpoints require:

```http
Authorization: Bearer <your-token>
```

For browser SSE usage, the frontend can append `admin_token` as a query parameter when needed.

---

## Current Status

The project currently includes:
- a working management dashboard
- member and invite operations
- Realtime Sync V2 scheduling
- SSE-driven dashboard updates
- polished workspace card UI

It is in a good state for **demo, staging, and small production/internal usage**, with the main known issue being the need to investigate the unusually long backend test run.

---

## Known Limitations

- SSE broker is currently in-memory, so it is best suited for single-instance deployment.
- Full backend pytest runtime needs further investigation.
- For larger scale deployments, a shared pub/sub layer such as Redis would be a stronger realtime foundation.

---

## Recommended Next Steps

1. Investigate the hanging backend test run
2. Re-run backend and frontend tests cleanly
3. Deploy to staging
4. If multi-instance scale is needed, upgrade realtime broker infrastructure
