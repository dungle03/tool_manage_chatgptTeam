# ChatGPT Workspace Manager

A full-stack dashboard for managing multiple **ChatGPT Team / Workspace** accounts from one place.

The project combines a **Next.js frontend** with a **FastAPI backend** to import workspaces, inspect members and invites, perform admin actions, and keep the dashboard fresh through **background sync + SSE realtime updates**.

---

## Overview

This repository is designed for operators who manage multiple ChatGPT team workspaces and need a single interface to:

- import and monitor team workspaces
- inspect member and invite state quickly
- kick members and manage pending invites
- trigger manual syncs when needed
- receive near-realtime updates without refreshing the page

The current codebase is in a strong state for **demo, internal use, and small single-instance deployments**.

---

## Key Features

### Workspace operations
- Import a workspace using `access_token` or `session_token`
- Display all managed workspaces in a unified dashboard
- Show seat usage, sync health, expiry date, and hot-sync state
- Delete a workspace from local management
- Trigger manual sync per workspace

### Member management
- View members for each workspace
- Show join date in `dd/mm/yyyy` format
- Kick members with a confirmation flow
- Highlight over-limit members directly in the table
- Current business rule: **7 seats per team are allowed; the 8th active member onward is highlighted in red**

### Invite management
- Send a new invite by email
- Resend a pending invite
- Cancel a pending invite
- Track pending invites per workspace

### Realtime Sync V2
- FastAPI background worker starts with app lifespan
- Smart scheduling via hot queue + follow-up sync windows
- Manual actions automatically trigger follow-up sync
- SSE stream pushes workspace updates to the dashboard
- Frontend deduplicates repeated toasts/events for a smoother UX

### UI/UX
- Modern dark dashboard UI
- Expandable workspace cards with animated chevron
- Status badges for sync state and hot workspaces
- Compact operational layout for high-density workspace management

---

## Architecture

```text
Frontend (Next.js / React)
        |
        v
Backend API (FastAPI)
        |
        +--> SQLite database
        +--> Background sync scheduler/worker
        +--> SSE event stream
        +--> ChatGPT internal/team APIs
```

### Repository structure

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
│  ├─ pytest.ini
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/
│  ├─ src/components/
│  ├─ src/lib/
│  ├─ src/types/
│  └─ package.json
├─ docs/
│  ├─ DESIGN.md
│  └─ PROJECT_REVIEW_20260312.md
├─ run_backend_tests.ps1
└─ README.md
```

---

## Tech Stack

| Layer | Technology |
|------|------------|
| Frontend | Next.js 14, React 18, TypeScript |
| Styling | Vanilla CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| Realtime | Server-Sent Events (SSE) |
| Backend tests | pytest |
| Frontend tests | Vitest, Testing Library |

---

## Current Project Status

### What is working well
- Workspace import and dashboard listing
- Member list retrieval and display
- Invite flow: create, resend, cancel
- Member removal flow
- Background sync lifecycle integrated with FastAPI
- Realtime dashboard refresh via SSE
- Improved workspace card UX and operational visibility
- Frontend test stack stabilized on Windows
- Backend test execution issue identified and documented

### Important operational note about backend tests
The backend suite can appear to “hang” if it is run from the **repository root** with:

```powershell
python -m pytest backend/tests
```

The correct and stable approaches are:

```powershell
# From repo root
./run_backend_tests.ps1

# Or directly inside backend/
python -m pytest tests -vv
```

This project now includes `run_backend_tests.ps1` to standardize backend test execution from the correct working directory.

---

## Getting Started

## 1. Backend setup

Create a virtual environment and install dependencies:

```powershell
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Create `backend/.env` from `backend/.env.example` if needed.

Run the backend **from the `backend/` directory**:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 2. Frontend setup

```powershell
cd frontend
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000).

---

## Environment Variables

### Backend (`backend/.env`)

| Variable | Default | Purpose |
|----------|---------|---------|
| `DATABASE_URL` | `sqlite:///./workspace_manager.db` | Backend database connection |
| `SYNC_LOOP_INTERVAL_SECONDS` | `5` | Main background loop interval |
| `SYNC_STALE_MINUTES` | `5` | Stale workspace threshold |
| `SYNC_PENDING_INVITE_SECONDS` | `15` | Faster checks for pending invites |
| `SYNC_BASELINE_MINUTES` | `5` | Baseline refresh cadence |
| `SYNC_HOT_WINDOW_SECONDS` | `180` | Duration a workspace stays “hot” |
| `SYNC_FOLLOWUP_STEPS` | `5,15,30,60` | Follow-up sync windows after important actions |
| `SYNC_ERROR_RETRY_STEPS` | `10,30,60` | Retry windows after sync failures |
| `SYNC_MAX_PARALLEL_WORKSPACES` | `2` | Max concurrent workspace syncs |
| `ADMIN_TOKEN` | unset | Protect backend admin endpoints |
| `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC` | unset | Disable background sync during tests / isolated runs |

### Frontend (`frontend/.env.local`)

| Variable | Purpose |
|----------|---------|
| `NEXT_PUBLIC_ADMIN_TOKEN` | Token forwarded by the dashboard to the backend |

---

## API Surface

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/workspaces` | List managed workspaces |
| `POST` | `/api/teams/import` | Import team/workspace from token(s) |
| `GET` | `/api/workspaces/{id}/members` | Get workspace members |
| `GET` | `/api/workspaces/{id}/sync` | Trigger immediate sync |
| `DELETE` | `/api/workspaces/{id}` | Remove workspace from local management |
| `POST` | `/api/invite` | Create invite |
| `GET` | `/api/invites?org_id=...` | List pending invites |
| `POST` | `/api/resend-invite` | Resend invite |
| `DELETE` | `/api/cancel-invite` | Cancel invite |
| `DELETE` | `/api/member` | Kick member |
| `GET` | `/api/events/workspaces` | Open SSE workspace event stream |

---

## Testing

### Frontend
Run from the real project path on Windows for the most reliable Vitest behavior:

```powershell
cd frontend
npm test
```

Optional production check:

```powershell
npm run build
```

### Backend
Recommended:

```powershell
./run_backend_tests.ps1
```

Custom pytest args:

```powershell
./run_backend_tests.ps1 -PytestArgs @('tests', '-vv', '-x')
```

Alternative (directly from `backend/`):

```powershell
python -m pytest tests -vv
```

> Do **not** rely on `python -m pytest backend/tests` from the repository root. It can run in the wrong context and make the suite appear stuck.

---

## Review Summary (2026-03-12)

The latest project review is tracked in:

- [docs/PROJECT_REVIEW_20260312.md](file:///D:/laptrinh/laptrinh/code/LinhTinh/tool_manage_chatgptTeam/docs/PROJECT_REVIEW_20260312.md)

High-level conclusion:
- The product is feature-complete for its current internal scope
- Realtime behavior and dashboard usability are in a good state
- Test workflows are now better documented and more reliable
- The main scaling limitation remains the in-memory SSE/event model for multi-instance deployments

---

## Known Limitations

- SSE/event delivery is currently best suited for **single-instance deployment**
- SQLite is convenient for development and small internal deployments, but a larger rollout should move to PostgreSQL
- The project depends on ChatGPT internal/team APIs, so upstream response changes can require maintenance
- Frontend test commands are more reliable from the real Windows drive path than through a symlinked path

---

## Recommended Next Steps

- Add Redis/pub-sub if multi-instance realtime support is required
- Expand end-to-end coverage around SSE and sync scheduling
- Add deployment documentation for staging/production environments
- Consider PostgreSQL for shared/team deployment scenarios

---

## License / Usage Note

This repository is currently prepared as an internal operational tool. Review your organization’s security and compliance requirements before production rollout.
