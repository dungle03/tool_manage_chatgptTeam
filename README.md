# ChatGPT Workspace Manager

A unified web dashboard to manage multiple ChatGPT Team workspaces — view members, invite users, kick members, and track workspace capacity.

## Architecture

```
Frontend (Next.js) → Backend API (FastAPI) → ChatGPT Internal API
                          ↓
                    SQLite / PostgreSQL
```

## Quick Start

### Backend

```bash
cd backend
pip install -r requirements.txt

# Optional: create .env from template
cp .env.example .env

# Run server
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Run Tests

```bash
# Backend
cd backend && pytest -v

# Frontend
cd frontend && npm test
```

## API Endpoints

| Method | Endpoint                       | Description                 |
| ------ | ------------------------------ | --------------------------- |
| GET    | `/api/workspaces`              | List all workspaces         |
| GET    | `/api/workspaces/{id}/members` | List members of a workspace |
| POST   | `/api/invite`                  | Invite a member by email    |
| DELETE | `/api/member`                  | Kick (remove) a member      |
| GET    | `/api/invites`                 | List pending invites        |
| POST   | `/api/resend-invite`           | Resend a pending invite     |
| DELETE | `/api/cancel-invite`           | Cancel a pending invite     |

## Authentication

When `ADMIN_TOKEN` environment variable is set, all API endpoints require:

```
Authorization: Bearer <your-token>
```

In development (no `ADMIN_TOKEN` set), authentication is bypassed.

## Configuration

| Variable       | Default                            | Description                     |
| -------------- | ---------------------------------- | ------------------------------- |
| `DATABASE_URL` | `sqlite:///./workspace_manager.db` | Database connection string      |
| `ADMIN_TOKEN`  | _(none)_                           | API authentication token        |
| `CORS_ORIGINS` | `http://localhost:3000`            | Comma-separated allowed origins |

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Pydantic
- **Frontend:** TypeScript, React, Next.js
- **Database:** SQLite (dev) / PostgreSQL (prod)
- **Testing:** pytest (backend), Vitest (frontend)
