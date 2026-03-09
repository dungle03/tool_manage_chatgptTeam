# ChatGPT Workspace Manager v1 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build one unified dashboard to manage multiple ChatGPT Team workspaces, including member listing (name/email/join date/status), basic invite flow, and kick member action.

**Architecture:** Use a FastAPI backend with PostgreSQL (SQLite in tests) exposing exactly 7 endpoints from `plan.md`. Use a Next.js frontend that consumes only those backend endpoints. Keep logic simple: thin routes, service functions, and predictable UI state transitions.

**Tech Stack:** FastAPI, SQLAlchemy, Pydantic, pytest, Next.js (App Router), TypeScript, TailwindCSS, shadcn/ui, React Testing Library, Vitest.

---

## Execution rules (must follow)
- Use @superpowers:test-driven-development for every task.
- Keep DRY + YAGNI: no redeem code feature in v1.
- Make one small commit per task.
- Before marking done, use @superpowers:verification-before-completion.

---

### Task 1: Bootstrap backend skeleton and endpoint contract

**Files:**
- Create: `backend/requirements.txt`
- Create: `backend/pytest.ini`
- Create: `backend/app/main.py`
- Create: `backend/app/routers/workspaces.py`
- Create: `backend/app/routers/members.py`
- Create: `backend/app/routers/invites.py`
- Create: `backend/tests/test_api_contract.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_api_contract.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_required_paths_exist_in_openapi():
    paths = set(app.openapi()["paths"].keys())
    assert "/api/workspaces" in paths
    assert "/api/workspaces/{id}/members" in paths
    assert "/api/invite" in paths
    assert "/api/member" in paths
    assert "/api/invites" in paths
    assert "/api/resend-invite" in paths
    assert "/api/cancel-invite" in paths
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_api_contract.py -v`
Expected: FAIL with import/module errors or missing paths.

**Step 3: Write minimal implementation**

```python
# backend/app/main.py
from fastapi import FastAPI
from app.routers import workspaces, members, invites

app = FastAPI(title="Workspace Manager API")
app.include_router(workspaces.router)
app.include_router(members.router)
app.include_router(invites.router)
```

```python
# backend/app/routers/workspaces.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/workspaces")
def get_workspaces():
    return []

@router.get("/api/workspaces/{id}/members")
def get_workspace_members(id: str):
    return []
```

```python
# backend/app/routers/members.py
from fastapi import APIRouter

router = APIRouter()

@router.post("/api/invite")
def invite_member(payload: dict):
    return {"ok": True, "payload": payload}

@router.delete("/api/member")
def delete_member(payload: dict):
    return {"ok": True, "payload": payload}
```

```python
# backend/app/routers/invites.py
from fastapi import APIRouter

router = APIRouter()

@router.get("/api/invites")
def get_invites(org_id: str):
    return []

@router.post("/api/resend-invite")
def resend_invite(payload: dict):
    return {"ok": True, "payload": payload}

@router.delete("/api/cancel-invite")
def cancel_invite(payload: dict):
    return {"ok": True, "payload": payload}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_api_contract.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/requirements.txt backend/pytest.ini backend/app/main.py backend/app/routers/workspaces.py backend/app/routers/members.py backend/app/routers/invites.py backend/tests/test_api_contract.py
git commit -m "chore: scaffold backend API contract routes"
```

---

### Task 2: Add database models and test fixtures

**Files:**
- Create: `backend/app/db.py`
- Create: `backend/app/models.py`
- Create: `backend/app/schemas.py`
- Create: `backend/tests/conftest.py`
- Create: `backend/tests/test_models_smoke.py`
- Modify: `backend/app/main.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_models_smoke.py
from app.models import Workspace, Member, Invite


def test_model_fields_exist():
    assert hasattr(Workspace, "org_id")
    assert hasattr(Member, "invite_date")
    assert hasattr(Invite, "invite_id")
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_models_smoke.py -v`
Expected: FAIL with `ModuleNotFoundError: app.models`.

**Step 3: Write minimal implementation**

```python
# backend/app/models.py
from sqlalchemy import String, Integer, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime

class Base(DeclarativeBase):
    pass

class Workspace(Base):
    __tablename__ = "workspaces"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    member_limit: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Member(Base):
    __tablename__ = "members"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    name: Mapped[str] = mapped_column(String)
    role: Mapped[str] = mapped_column(String)
    status: Mapped[str] = mapped_column(String)
    invite_date: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Invite(Base):
    __tablename__ = "invites"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org_id: Mapped[str] = mapped_column(String, index=True)
    email: Mapped[str] = mapped_column(String, index=True)
    invite_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    status: Mapped[str] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.models import Base

DATABASE_URL = "sqlite:///./workspace_manager.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

def get_session():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()

def init_db():
    Base.metadata.create_all(bind=engine)
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_models_smoke.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/db.py backend/app/models.py backend/app/schemas.py backend/tests/conftest.py backend/tests/test_models_smoke.py backend/app/main.py
git commit -m "feat: add core SQLAlchemy models and DB session"
```

---

### Task 3: Implement `GET /api/workspaces`

**Files:**
- Modify: `backend/app/routers/workspaces.py`
- Modify: `backend/app/schemas.py`
- Create: `backend/tests/test_get_workspaces.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_get_workspaces.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_workspaces_returns_list(seed_data):
    response = client.get("/api/workspaces")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert data[0]["org_id"] == "org_001"
    assert "member_limit" in data[0]
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_get_workspaces.py::test_get_workspaces_returns_list -v`
Expected: FAIL because route returns empty list or missing seeded data.

**Step 3: Write minimal implementation**

```python
# backend/app/routers/workspaces.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_session
from app.models import Workspace

router = APIRouter()

@router.get("/api/workspaces")
def get_workspaces(session: Session = Depends(get_session)):
    rows = session.execute(select(Workspace)).scalars().all()
    return [
        {
            "id": row.id,
            "org_id": row.org_id,
            "name": row.name,
            "member_limit": row.member_limit,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_get_workspaces.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/routers/workspaces.py backend/app/schemas.py backend/tests/test_get_workspaces.py
git commit -m "feat: implement get workspaces endpoint"
```

---

### Task 4: Implement `GET /api/workspaces/{id}/members`

**Files:**
- Modify: `backend/app/routers/workspaces.py`
- Create: `backend/tests/test_get_workspace_members.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_get_workspace_members.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_workspace_members_returns_required_fields(seed_data):
    response = client.get("/api/workspaces/org_001/members")
    assert response.status_code == 200
    member = response.json()[0]
    assert set(["name", "email", "invite_date", "role", "status"]).issubset(member.keys())
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_get_workspace_members.py -v`
Expected: FAIL due to empty response or missing fields.

**Step 3: Write minimal implementation**

```python
# backend/app/routers/workspaces.py
from app.models import Member

@router.get("/api/workspaces/{id}/members")
def get_workspace_members(id: str, session: Session = Depends(get_session)):
    rows = session.execute(
        select(Member).where(Member.org_id == id)
    ).scalars().all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "role": row.role,
            "status": row.status,
            "invite_date": row.invite_date.isoformat() if row.invite_date else None,
        }
        for row in rows
    ]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_get_workspace_members.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/routers/workspaces.py backend/tests/test_get_workspace_members.py
git commit -m "feat: implement get workspace members endpoint"
```

---

### Task 5: Implement `POST /api/invite` and `GET /api/invites`

**Files:**
- Modify: `backend/app/routers/members.py`
- Modify: `backend/app/routers/invites.py`
- Create: `backend/tests/test_invite_flow.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_invite_flow.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_invite_then_list_invites(seed_data):
    payload = {"org_id": "org_001", "email": "new@company.com", "role": "member"}
    create_res = client.post("/api/invite", json=payload)
    assert create_res.status_code == 200

    list_res = client.get("/api/invites", params={"org_id": "org_001"})
    assert list_res.status_code == 200
    emails = [x["email"] for x in list_res.json()]
    assert "new@company.com" in emails
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_invite_flow.py -v`
Expected: FAIL because invite is not persisted.

**Step 3: Write minimal implementation**

```python
# backend/app/routers/members.py
from datetime import datetime
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.db import get_session
from app.models import Invite

router = APIRouter()

@router.post("/api/invite")
def invite_member(payload: dict, session: Session = Depends(get_session)):
    org_id = payload.get("org_id")
    email = payload.get("email")
    role = payload.get("role", "member")
    if not org_id or not email:
        raise HTTPException(status_code=400, detail="org_id and email are required")

    invite = Invite(
        org_id=org_id,
        email=email,
        invite_id=f"inv_{uuid4().hex[:10]}",
        status="pending",
        created_at=datetime.utcnow(),
    )
    session.add(invite)
    session.commit()
    return {"ok": True, "invite_id": invite.invite_id, "role": role}
```

```python
# backend/app/routers/invites.py
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from app.db import get_session
from app.models import Invite

router = APIRouter()

@router.get("/api/invites")
def get_invites(org_id: str, session: Session = Depends(get_session)):
    rows = session.execute(select(Invite).where(Invite.org_id == org_id)).scalars().all()
    return [
        {
            "id": row.id,
            "org_id": row.org_id,
            "email": row.email,
            "invite_id": row.invite_id,
            "status": row.status,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_invite_flow.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/routers/members.py backend/app/routers/invites.py backend/tests/test_invite_flow.py
git commit -m "feat: implement invite create and list endpoints"
```

---

### Task 6: Implement `POST /api/resend-invite` and `DELETE /api/cancel-invite`

**Files:**
- Modify: `backend/app/routers/invites.py`
- Create: `backend/tests/test_invite_actions.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_invite_actions.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_resend_and_cancel_invite(seed_data):
    resend = client.post("/api/resend-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"})
    assert resend.status_code == 200
    assert resend.json()["status"] == "pending"

    cancel = client.request("DELETE", "/api/cancel-invite", json={"org_id": "org_001", "invite_id": "inv_seed_1"})
    assert cancel.status_code == 200
    assert cancel.json()["status"] == "cancelled"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_invite_actions.py -v`
Expected: FAIL due to no state update.

**Step 3: Write minimal implementation**

```python
# backend/app/routers/invites.py
from fastapi import HTTPException

@router.post("/api/resend-invite")
def resend_invite(payload: dict, session: Session = Depends(get_session)):
    org_id = payload.get("org_id")
    invite_id = payload.get("invite_id")
    row = session.execute(
        select(Invite).where(Invite.org_id == org_id, Invite.invite_id == invite_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="invite not found")
    row.status = "pending"
    session.commit()
    return {"ok": True, "status": row.status, "invite_id": row.invite_id}

@router.delete("/api/cancel-invite")
def cancel_invite(payload: dict, session: Session = Depends(get_session)):
    org_id = payload.get("org_id")
    invite_id = payload.get("invite_id")
    row = session.execute(
        select(Invite).where(Invite.org_id == org_id, Invite.invite_id == invite_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="invite not found")
    row.status = "cancelled"
    session.commit()
    return {"ok": True, "status": row.status, "invite_id": row.invite_id}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_invite_actions.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/routers/invites.py backend/tests/test_invite_actions.py
git commit -m "feat: add resend and cancel invite endpoints"
```

---

### Task 7: Implement `DELETE /api/member` (kick member)

**Files:**
- Modify: `backend/app/routers/members.py`
- Create: `backend/tests/test_kick_member.py`

**Step 1: Write the failing test**

```python
# backend/tests/test_kick_member.py
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_kick_member_sets_removed_status(seed_data):
    payload = {"org_id": "org_001", "member_id": 1}
    response = client.request("DELETE", "/api/member", json=payload)
    assert response.status_code == 200
    assert response.json()["status"] == "removed"
```

**Step 2: Run test to verify it fails**

Run: `cd backend && pytest tests/test_kick_member.py -v`
Expected: FAIL because member row is not updated.

**Step 3: Write minimal implementation**

```python
# backend/app/routers/members.py
from sqlalchemy import select
from app.models import Member

@router.delete("/api/member")
def delete_member(payload: dict, session: Session = Depends(get_session)):
    org_id = payload.get("org_id")
    member_id = payload.get("member_id")
    row = session.execute(
        select(Member).where(Member.org_id == org_id, Member.id == member_id)
    ).scalar_one_or_none()
    if not row:
        raise HTTPException(status_code=404, detail="member not found")
    if row.role.lower() == "owner":
        raise HTTPException(status_code=409, detail="cannot remove owner")
    row.status = "removed"
    session.commit()
    return {"ok": True, "member_id": row.id, "status": row.status}
```

**Step 4: Run test to verify it passes**

Run: `cd backend && pytest tests/test_kick_member.py -v`
Expected: PASS.

**Step 5: Commit**

```bash
git add backend/app/routers/members.py backend/tests/test_kick_member.py
git commit -m "feat: implement member kick endpoint"
```

---

### Task 8: Create frontend app shell and typed API client

**Files:**
- Create: `frontend/package.json`
- Create: `frontend/src/types/api.ts`
- Create: `frontend/src/lib/api.ts`
- Create: `frontend/src/__tests__/api-client.test.ts`

**Step 1: Write the failing test**

```ts
// frontend/src/__tests__/api-client.test.ts
import { describe, it, expect, vi } from "vitest";
import { getWorkspaces } from "@/lib/api";

describe("api client", () => {
  it("calls GET /api/workspaces", async () => {
    const mockFetch = vi.fn().mockResolvedValue({
      ok: true,
      json: async () => [],
    });
    vi.stubGlobal("fetch", mockFetch as any);

    await getWorkspaces();
    expect(mockFetch).toHaveBeenCalledWith("/api/workspaces", expect.any(Object));
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- api-client.test.ts`
Expected: FAIL with missing module/function.

**Step 3: Write minimal implementation**

```ts
// frontend/src/lib/api.ts
export async function getWorkspaces() {
  const res = await fetch("/api/workspaces", { method: "GET" });
  if (!res.ok) throw new Error("Failed to fetch workspaces");
  return res.json();
}

export async function getWorkspaceMembers(orgId: string) {
  const res = await fetch(`/api/workspaces/${orgId}/members`, { method: "GET" });
  if (!res.ok) throw new Error("Failed to fetch members");
  return res.json();
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- api-client.test.ts`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/package.json frontend/src/types/api.ts frontend/src/lib/api.ts frontend/src/__tests__/api-client.test.ts
git commit -m "feat: add typed frontend API client"
```

---

### Task 9: Build unified dashboard with team overview and member table

**Files:**
- Create: `frontend/src/app/page.tsx`
- Create: `frontend/src/components/dashboard-summary.tsx`
- Create: `frontend/src/components/workspace-card.tsx`
- Create: `frontend/src/components/member-table.tsx`
- Create: `frontend/src/__tests__/dashboard-page.test.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/src/__tests__/dashboard-page.test.tsx
import { render, screen } from "@testing-library/react";
import DashboardPage from "@/app/page";

it("renders workspace summary labels", async () => {
  render(<DashboardPage />);
  expect(screen.getByText("Total teams")).toBeInTheDocument();
  expect(screen.getByText("Total members")).toBeInTheDocument();
  expect(screen.getByText("Pending invites")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- dashboard-page.test.tsx`
Expected: FAIL because dashboard components do not exist.

**Step 3: Write minimal implementation**

```tsx
// frontend/src/app/page.tsx
import { DashboardSummary } from "@/components/dashboard-summary";
import { WorkspaceCard } from "@/components/workspace-card";

export default function DashboardPage() {
  return (
    <main className="p-6 space-y-6">
      <DashboardSummary totalTeams={0} totalMembers={0} pendingInvites={0} syncErrors={0} />
      <WorkspaceCard title="No teams yet" members={0} memberLimit={0} status="synced" />
    </main>
  );
}
```

```tsx
// frontend/src/components/dashboard-summary.tsx
export function DashboardSummary(props: { totalTeams: number; totalMembers: number; pendingInvites: number; syncErrors: number; }) {
  return (
    <section className="grid grid-cols-4 gap-3">
      <div>Total teams: {props.totalTeams}</div>
      <div>Total members: {props.totalMembers}</div>
      <div>Pending invites: {props.pendingInvites}</div>
      <div>Sync errors: {props.syncErrors}</div>
    </section>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- dashboard-page.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/app/page.tsx frontend/src/components/dashboard-summary.tsx frontend/src/components/workspace-card.tsx frontend/src/components/member-table.tsx frontend/src/__tests__/dashboard-page.test.tsx
git commit -m "feat: add unified dashboard skeleton and summary"
```

---

### Task 10: Add kick action UI and invite management UI

**Files:**
- Modify: `frontend/src/components/member-table.tsx`
- Create: `frontend/src/components/invite-panel.tsx`
- Create: `frontend/src/components/invite-list.tsx`
- Create: `frontend/src/__tests__/member-actions.test.tsx`
- Create: `frontend/src/__tests__/invite-panel.test.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/src/__tests__/member-actions.test.tsx
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemberTable } from "@/components/member-table";

it("shows Kick button and confirmation", async () => {
  const user = userEvent.setup();
  render(<MemberTable members={[{ id: 1, name: "A", email: "a@x.com", role: "member", status: "active", invite_date: null }]} />);
  await user.click(screen.getByRole("button", { name: "Kick" }));
  expect(screen.getByText("Confirm kick member")).toBeInTheDocument();
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- member-actions.test.tsx invite-panel.test.tsx`
Expected: FAIL because modal/panel behavior does not exist.

**Step 3: Write minimal implementation**

```tsx
// frontend/src/components/member-table.tsx
"use client";
import { useState } from "react";

export function MemberTable({ members }: { members: any[] }) {
  const [target, setTarget] = useState<any | null>(null);

  return (
    <div>
      <table className="w-full">
        <thead><tr><th>Name</th><th>Email</th><th>Join Date</th><th>Status</th><th>Action</th></tr></thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.id}>
              <td>{m.name}</td>
              <td>{m.email}</td>
              <td>{m.invite_date || "-"}</td>
              <td>{m.status}</td>
              <td><button onClick={() => setTarget(m)}>Kick</button></td>
            </tr>
          ))}
        </tbody>
      </table>

      {target && (
        <div>
          <p>Confirm kick member</p>
          <p>{target.email}</p>
          <button onClick={() => setTarget(null)}>Cancel</button>
          <button>Confirm</button>
        </div>
      )}
    </div>
  );
}
```

```tsx
// frontend/src/components/invite-panel.tsx
"use client";
import { useState } from "react";

export function InvitePanel({ onInvite }: { onInvite: (email: string, role: string) => Promise<void> }) {
  const [email, setEmail] = useState("");
  const [role, setRole] = useState("member");

  return (
    <form
      onSubmit={async (e) => {
        e.preventDefault();
        await onInvite(email, role);
      }}
      className="space-y-2"
    >
      <input value={email} onChange={(e) => setEmail(e.target.value)} placeholder="Email" />
      <select value={role} onChange={(e) => setRole(e.target.value)}>
        <option value="member">member</option>
        <option value="admin">admin</option>
      </select>
      <button type="submit">Send Invite</button>
    </form>
  );
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- member-actions.test.tsx invite-panel.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/components/member-table.tsx frontend/src/components/invite-panel.tsx frontend/src/components/invite-list.tsx frontend/src/__tests__/member-actions.test.tsx frontend/src/__tests__/invite-panel.test.tsx
git commit -m "feat: add kick confirmation and invite management UI"
```

---

### Task 11: Wire frontend actions to backend endpoints and add error states

**Files:**
- Modify: `frontend/src/lib/api.ts`
- Modify: `frontend/src/app/page.tsx`
- Create: `frontend/src/__tests__/endpoint-wiring.test.tsx`

**Step 1: Write the failing test**

```tsx
// frontend/src/__tests__/endpoint-wiring.test.tsx
import { inviteMember, kickMember, listInvites, resendInvite, cancelInvite } from "@/lib/api";
import { describe, it, expect, vi } from "vitest";

describe("endpoint wiring", () => {
  it("hits required backend API paths", async () => {
    const mockFetch = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", mockFetch as any);

    await inviteMember({ org_id: "org_001", email: "a@x.com", role: "member" });
    await kickMember({ org_id: "org_001", member_id: 1 });
    await listInvites("org_001");
    await resendInvite({ org_id: "org_001", invite_id: "inv_1" });
    await cancelInvite({ org_id: "org_001", invite_id: "inv_1" });

    const calledUrls = mockFetch.mock.calls.map((x: any[]) => x[0]);
    expect(calledUrls).toContain("/api/invite");
    expect(calledUrls).toContain("/api/member");
    expect(calledUrls).toContain("/api/invites?org_id=org_001");
    expect(calledUrls).toContain("/api/resend-invite");
    expect(calledUrls).toContain("/api/cancel-invite");
  });
});
```

**Step 2: Run test to verify it fails**

Run: `cd frontend && npm test -- endpoint-wiring.test.tsx`
Expected: FAIL because action methods are missing.

**Step 3: Write minimal implementation**

```ts
// frontend/src/lib/api.ts
export async function inviteMember(payload: { org_id: string; email: string; role: string }) {
  return requestJson("/api/invite", "POST", payload);
}

export async function kickMember(payload: { org_id: string; member_id: number }) {
  return requestJson("/api/member", "DELETE", payload);
}

export async function listInvites(orgId: string) {
  return requestJson(`/api/invites?org_id=${orgId}`, "GET");
}

export async function resendInvite(payload: { org_id: string; invite_id: string }) {
  return requestJson("/api/resend-invite", "POST", payload);
}

export async function cancelInvite(payload: { org_id: string; invite_id: string }) {
  return requestJson("/api/cancel-invite", "DELETE", payload);
}

async function requestJson(url: string, method: string, body?: unknown) {
  const res = await fetch(url, {
    method,
    headers: { "Content-Type": "application/json" },
    body: body ? JSON.stringify(body) : undefined,
  });
  if (!res.ok) throw new Error(`Request failed: ${method} ${url}`);
  return res.json();
}
```

**Step 4: Run test to verify it passes**

Run: `cd frontend && npm test -- endpoint-wiring.test.tsx`
Expected: PASS.

**Step 5: Commit**

```bash
git add frontend/src/lib/api.ts frontend/src/app/page.tsx frontend/src/__tests__/endpoint-wiring.test.tsx
git commit -m "feat: wire frontend actions to required backend endpoints"
```

---

### Task 12: Full verification + runbook

**Files:**
- Create: `docs/plans/2026-03-09-workspace-manager-test-report.md`
- Modify: `README.md` (if repository uses README)

**Step 1: Write the failing test/checklist artifact**

```md
# Workspace Manager v1 Verification Checklist

- [ ] Backend tests pass
- [ ] Frontend tests pass
- [ ] Required 7 endpoints available
- [ ] Dashboard shows teams + members + statuses
- [ ] Invite, resend, cancel, kick flows work
```

**Step 2: Run verification commands (expect at least one failure first)**

Run: `cd backend && pytest -v`
Expected: Initial FAIL until all remaining red tests are fixed.

Run: `cd frontend && npm test`
Expected: Initial FAIL until all component wiring is complete.

**Step 3: Complete minimal fixes and finalize docs**

```md
# docs/plans/2026-03-09-workspace-manager-test-report.md

## Backend
- Command: `cd backend && pytest -v`
- Result: PASS

## Frontend
- Command: `cd frontend && npm test`
- Result: PASS

## API Contract
Confirmed endpoints:
- GET /api/workspaces
- GET /api/workspaces/{id}/members
- POST /api/invite
- DELETE /api/member
- GET /api/invites
- POST /api/resend-invite
- DELETE /api/cancel-invite
```

**Step 4: Run final verification to verify it passes**

Run: `cd backend && pytest -v && cd ../frontend && npm test`
Expected: PASS for both suites.

**Step 5: Commit**

```bash
git add docs/plans/2026-03-09-workspace-manager-test-report.md README.md
git commit -m "docs: add verification report and runbook for workspace manager v1"
```

---

## Definition of Done
- All 7 backend endpoints implemented exactly as required by `plan.md` section 7.
- Dashboard shows multi-team overview and per-team members with name/email/join date/status.
- Basic invite flow works (create/list/resend/cancel).
- Kick member flow works with confirmation.
- Backend + frontend automated tests pass.
- Verification report committed.
