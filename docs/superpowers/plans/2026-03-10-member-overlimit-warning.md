# Member Over-Limit Warning Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Persist ChatGPT Date added correctly and highlight only active members beyond the oldest 5 in red rows to speed up kick decisions.

**Architecture:** Extend backend member sync mapping so `members.created_at` is populated from ChatGPT `created_time` with deterministic fallbacks. Compute over-limit flags in `MemberTable` from active members only using deterministic sorting and apply row-level warning styling. Cover rules with backend and frontend tests so behavior stays stable.

**Tech Stack:** FastAPI, SQLAlchemy, pytest, Next.js 14, React, TypeScript, Vitest, Testing Library.

---

## File structure and responsibilities

- `backend/app/routers/workspaces.py`
  - Keep sync endpoint behavior, but centralize member Date added extraction (`created_time` primary; legacy fallbacks) and ensure UTC normalization.
- `backend/tests/test_workspace_sync.py`
  - Verify sync persists `members.created_at` from `created_time` and legacy fallback fields.
- `frontend/src/components/member-table.tsx`
  - Compute deterministic over-limit member IDs (active-only, known-date-only, stable tie-breaks) and attach warning row class.
- `frontend/src/app/globals.css`
  - Define visual style for over-limit member rows without changing kick/protected actions.
- `frontend/src/__tests__/member-table-overlimit.test.tsx` (new)
  - Focused rule tests for active-only counting, pending excluded, <=5 no warning, 6th+ warning, deterministic tie-breaks, unknown-date behavior.

## Chunk 1: Backend Date added mapping

### Task 1: Add failing backend tests for created_time priority and UTC normalization

**Files:**
- Modify: `backend/tests/test_workspace_sync.py`

- [ ] **Step 1: Ensure pytest import exists**

At top of `backend/tests/test_workspace_sync.py`, ensure:

```python
import pytest
```

- [ ] **Step 2: Write failing test for created_time priority + UTC normalization**

```python
def test_sync_workspace_prefers_created_time_and_normalizes_to_utc(seed_data, monkeypatch):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        return [
            {
                "id": "user_1",
                "email": "remote-user@company.com",
                "name": "Remote User",
                "role": "standard-user",
                "status": "active",
                "created_time": "2026-03-09T15:30:00+07:00",
                "created_at": "2026-03-09T00:00:00Z",
                "created": "2026-03-09T01:00:00Z",
            }
        ]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_members", fake_get_members)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    sync_response = client.get("/api/workspaces/org_001/sync")
    assert sync_response.status_code == 200

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200
    data = members_response.json()
    assert len(data) == 1
    assert data[0]["created_at"] == "2026-03-09T08:30:00+00:00"
```

- [ ] **Step 3: Run test to verify it fails**

Run: `pytest backend/tests/test_workspace_sync.py::test_sync_workspace_prefers_created_time_and_normalizes_to_utc -v`
Expected: FAIL because current sync ignores `created_time` and does not guarantee UTC normalization.

- [ ] **Step 4: Write minimal implementation**

In `backend/app/routers/workspaces.py`:

```python
created_raw = item.get("created_time") or item.get("created_at") or item.get("created")
created = _parse_datetime(created_raw)
```

Update `_parse_datetime` only to normalize parsed ISO datetimes to UTC (no epoch parsing in this task).

- [ ] **Step 5: Run test to verify it passes**

Run: `pytest backend/tests/test_workspace_sync.py::test_sync_workspace_prefers_created_time_and_normalizes_to_utc -v`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add backend/app/routers/workspaces.py backend/tests/test_workspace_sync.py
git commit -m "fix(sync): prioritize created_time and normalize member dates to utc"
```

### Task 2: Add failing backend tests for deterministic fallback order

**Files:**
- Modify: `backend/tests/test_workspace_sync.py`

- [ ] **Step 1: Write failing parameterized fallback-order tests**

```python
@pytest.mark.parametrize(
    "payload, expected_created_at",
    [
        (
            {
                "created_time": "2026-03-09T09:00:00Z",
                "created_at": "2026-03-09T10:00:00Z",
                "created": "2026-03-09T11:00:00Z",
            },
            "2026-03-09T09:00:00+00:00",
        ),
        (
            {
                "created_at": "2026-03-09T10:00:00Z",
                "created": "2026-03-09T11:00:00Z",
            },
            "2026-03-09T10:00:00+00:00",
        ),
        (
            {
                "created": "2026-03-09T11:00:00Z",
            },
            "2026-03-09T11:00:00+00:00",
        ),
    ],
)
def test_sync_workspace_uses_expected_date_field_priority(seed_data, monkeypatch, payload, expected_created_at):
    async def fake_refresh_access_token(_self, _session_token, _account_id=None):
        return {"access_token": "fresh-token", "session_token": _session_token}

    async def fake_get_members(_self, _access_token, _account_id):
        member = {
            "id": "user_1",
            "email": "remote-user@company.com",
            "name": "Remote User",
            "role": "standard-user",
            "status": "active",
        }
        member.update(payload)
        return [member]

    async def fake_get_invites(_self, _access_token, _account_id):
        return []

    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.refresh_access_token", fake_refresh_access_token)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_members", fake_get_members)
    monkeypatch.setattr("app.services.chatgpt.ChatGPTService.get_invites", fake_get_invites)

    sync_response = client.get("/api/workspaces/org_001/sync")
    assert sync_response.status_code == 200

    members_response = client.get("/api/workspaces/org_001/members")
    assert members_response.status_code == 200
    data = members_response.json()
    assert data[0]["created_at"] == expected_created_at
```

- [ ] **Step 2: Run test to verify behavior is locked**

Run: `pytest backend/tests/test_workspace_sync.py::test_sync_workspace_uses_expected_date_field_priority -v`
Expected: PASS (Task 1 implementation should already satisfy the required extraction priority; this test locks it against regression).

- [ ] **Step 3: Adjust implementation only if needed**

Ensure extraction order remains exactly:

```python
item.get("created_time") or item.get("created_at") or item.get("created")
```

- [ ] **Step 4: Run tests to verify it passes**

Run: `pytest backend/tests/test_workspace_sync.py::test_sync_workspace_uses_expected_date_field_priority -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/workspaces.py backend/tests/test_workspace_sync.py
git commit -m "test(sync): enforce member date extraction priority"
```

### Task 3: Add failing backend tests for epoch parsing and invalid-date behavior

**Files:**
- Modify: `backend/tests/test_workspace_sync.py`
- Modify: `backend/app/routers/workspaces.py`

- [ ] **Step 1: Write failing unit tests for `_parse_datetime`**

```python
from app.routers.workspaces import _parse_datetime


def test_parse_datetime_accepts_epoch_seconds():
    parsed = _parse_datetime(1741516200)
    assert parsed is not None
    assert parsed.isoformat() == "2025-03-09T10:30:00+00:00"


def test_parse_datetime_accepts_epoch_milliseconds():
    parsed = _parse_datetime(1741516200000)
    assert parsed is not None
    assert parsed.isoformat() == "2025-03-09T10:30:00+00:00"


def test_parse_datetime_returns_none_for_invalid_values():
    assert _parse_datetime("not-a-date") is None
    assert _parse_datetime("") is None
```

- [ ] **Step 2: Run tests to verify failures**

Run: `pytest backend/tests/test_workspace_sync.py::test_parse_datetime_accepts_epoch_seconds backend/tests/test_workspace_sync.py::test_parse_datetime_accepts_epoch_milliseconds backend/tests/test_workspace_sync.py::test_parse_datetime_returns_none_for_invalid_values -v`
Expected: FAIL before parser enhancement.

- [ ] **Step 3: Implement parser enhancement in `_parse_datetime`**

In `backend/app/routers/workspaces.py`:

```python
if isinstance(value, (int, float)):
    # detect ms vs s by magnitude
```

Also normalize all successful parses to UTC.

- [ ] **Step 4: Run full backend sync/date tests**

Run: `pytest backend/tests/test_workspace_sync.py -v`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/routers/workspaces.py backend/tests/test_workspace_sync.py
git commit -m "feat(sync): support epoch date parsing for member created_at"
```

## Chunk 2: Frontend over-limit classification and styling

### Task 3: Add failing frontend tests for over-limit logic

**Files:**
- Create: `frontend/src/__tests__/member-table-overlimit.test.tsx`

- [ ] **Step 1: Write failing tests**

```tsx
import { render, screen } from "@testing-library/react";
import { MemberTable } from "@/components/member-table";

function makeMember(overrides: Partial<any>) {
  return {
    id: 1,
    remote_id: "u-1",
    name: "Member",
    email: "member@example.com",
    role: "member",
    status: "active",
    invite_date: null,
    created_at: "2026-03-01T00:00:00Z",
    picture: null,
    ...overrides,
  };
}

it("does not highlight when active members are <= 5", () => {
  const members = [1, 2, 3, 4, 5].map((n) =>
    makeMember({ id: n, remote_id: `u-${n}`, email: `${n}@x.com`, created_at: `2026-03-0${n}T00:00:00Z` }),
  );

  render(<MemberTable members={members} />);

  expect(screen.getByText("1@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  expect(screen.getByText("5@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
});

it("highlights exactly 6th+ oldest active members", () => {
  const members = [1, 2, 3, 4, 5, 6, 7].map((n) =>
    makeMember({ id: n, remote_id: `u-${n}`, email: `${n}@x.com`, created_at: `2026-03-0${Math.min(n, 9)}T00:00:00Z` }),
  );

  render(<MemberTable members={members} />);

  expect(screen.getByText("5@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  expect(screen.getByText("6@x.com").closest("tr")).toHaveClass("member-overlimit-row");
  expect(screen.getByText("7@x.com").closest("tr")).toHaveClass("member-overlimit-row");
});

it("excludes generic non-active statuses from quota classification", () => {
  const members = [
    makeMember({ id: 1, remote_id: "u-1", email: "1@x.com", status: "active", created_at: "2026-03-02T00:00:00Z" }),
    makeMember({ id: 2, remote_id: "u-2", email: "2@x.com", status: "active", created_at: "2026-03-03T00:00:00Z" }),
    makeMember({ id: 3, remote_id: "u-3", email: "3@x.com", status: "active", created_at: "2026-03-04T00:00:00Z" }),
    makeMember({ id: 4, remote_id: "u-4", email: "4@x.com", status: "active", created_at: "2026-03-05T00:00:00Z" }),
    makeMember({ id: 5, remote_id: "u-5", email: "5@x.com", status: "active", created_at: "2026-03-06T00:00:00Z" }),
    makeMember({ id: 99, remote_id: "u-99", email: "99@x.com", status: "inactive", created_at: "2026-03-01T00:00:00Z" }),
  ];

  render(<MemberTable members={members} />);

  expect(screen.getByText("99@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  expect(screen.getByText("5@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
});

it("excludes pending members from quota classification", () => {
  const members = [
    makeMember({ id: 1, remote_id: "u-1", email: "1@x.com", status: "active", created_at: "2026-03-02T00:00:00Z" }),
    makeMember({ id: 2, remote_id: "u-2", email: "2@x.com", status: "active", created_at: "2026-03-03T00:00:00Z" }),
    makeMember({ id: 3, remote_id: "u-3", email: "3@x.com", status: "active", created_at: "2026-03-04T00:00:00Z" }),
    makeMember({ id: 4, remote_id: "u-4", email: "4@x.com", status: "active", created_at: "2026-03-05T00:00:00Z" }),
    makeMember({ id: 5, remote_id: "u-5", email: "5@x.com", status: "active", created_at: "2026-03-06T00:00:00Z" }),
    makeMember({ id: 88, remote_id: "u-88", email: "88@x.com", status: "pending", created_at: "2026-03-01T00:00:00Z" }),
  ];

  render(<MemberTable members={members} />);

  expect(screen.getByText("88@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  expect(screen.getByText("5@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
});

it("excludes unknown-date active members from classification", () => {
  const members = [
    makeMember({ id: 1, remote_id: "u-1", email: "1@x.com", status: "active", created_at: "2026-03-01T00:00:00Z" }),
    makeMember({ id: 2, remote_id: "u-2", email: "2@x.com", status: "active", created_at: "2026-03-02T00:00:00Z" }),
    makeMember({ id: 3, remote_id: "u-3", email: "3@x.com", status: "active", created_at: "2026-03-03T00:00:00Z" }),
    makeMember({ id: 4, remote_id: "u-4", email: "4@x.com", status: "active", created_at: "2026-03-04T00:00:00Z" }),
    makeMember({ id: 5, remote_id: "u-5", email: "5@x.com", status: "active", created_at: "2026-03-05T00:00:00Z" }),
    makeMember({ id: 6, remote_id: "u-6", email: "6@x.com", status: "active", created_at: "2026-03-06T00:00:00Z" }),
    makeMember({ id: 77, remote_id: "u-77", email: "77@x.com", status: "active", created_at: null }),
  ];

  render(<MemberTable members={members} />);

  expect(screen.getByText("77@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  expect(screen.getByText("5@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
  expect(screen.getByText("6@x.com").closest("tr")).toHaveClass("member-overlimit-row");
});

it("uses remote_id tie-break when created_at is equal", () => {
  const sameDate = "2026-03-10T00:00:00Z";
  const members = [
    makeMember({ id: 1, remote_id: "u-z", email: "z@x.com", created_at: sameDate }),
    makeMember({ id: 2, remote_id: "u-a", email: "a@x.com", created_at: sameDate }),
    makeMember({ id: 3, remote_id: "u-b", email: "b@x.com", created_at: sameDate }),
    makeMember({ id: 4, remote_id: "u-c", email: "c@x.com", created_at: sameDate }),
    makeMember({ id: 5, remote_id: "u-d", email: "d@x.com", created_at: sameDate }),
    makeMember({ id: 6, remote_id: "u-e", email: "e@x.com", created_at: sameDate }),
  ];

  render(<MemberTable members={members} />);

  expect(screen.getByText("z@x.com").closest("tr")).toHaveClass("member-overlimit-row");
  expect(screen.getByText("e@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
});

it("uses id tie-break when created_at and remote_id are equal", () => {
  const sameDate = "2026-03-10T00:00:00Z";
  const members = [
    makeMember({ id: 60, remote_id: null, email: "60@x.com", created_at: sameDate }),
    makeMember({ id: 10, remote_id: null, email: "10@x.com", created_at: sameDate }),
    makeMember({ id: 50, remote_id: null, email: "50@x.com", created_at: sameDate }),
    makeMember({ id: 20, remote_id: null, email: "20@x.com", created_at: sameDate }),
    makeMember({ id: 40, remote_id: null, email: "40@x.com", created_at: sameDate }),
    makeMember({ id: 30, remote_id: null, email: "30@x.com", created_at: sameDate }),
  ];

  render(<MemberTable members={members} />);

  expect(screen.getByText("60@x.com").closest("tr")).toHaveClass("member-overlimit-row");
  expect(screen.getByText("30@x.com").closest("tr")).not.toHaveClass("member-overlimit-row");
});
```

- [ ] **Step 2: Run tests to verify failures**

Run: `cd frontend && npm test -- src/__tests__/member-table-overlimit.test.tsx`
Expected: FAIL before component logic/style exists.

- [ ] **Step 3: Commit (optional checkpoint)**

```bash
git add frontend/src/__tests__/member-table-overlimit.test.tsx
git commit -m "test(frontend): add over-limit member classification tests"
```

### Task 4: Implement minimal frontend over-limit classification

**Files:**
- Modify: `frontend/src/components/member-table.tsx`

- [ ] **Step 1: Implement deterministic classification helper in component**

Add local helper(s) in `MemberTable`:

```tsx
function isActive(status: string): boolean {
  return status.trim().toLowerCase() === "active";
}

function toTimestamp(value: string | null): number | null {
  if (!value) return null;
  const parsed = Date.parse(value);
  return Number.isNaN(parsed) ? null : parsed;
}
```

Compute over-limit set once per render:

```tsx
const eligible = members
  .filter((member) => isActive(member.status))
  .map((member) => ({ member, ts: toTimestamp(member.created_at) }))
  .filter((entry) => entry.ts !== null)
  .sort((a, b) => {
    if (a.ts! !== b.ts!) return a.ts! - b.ts!;
    const aRemote = a.member.remote_id ?? "";
    const bRemote = b.member.remote_id ?? "";
    if (aRemote !== bRemote) return aRemote.localeCompare(bRemote);
    return a.member.id - b.member.id;
  });

const overLimitIds = new Set(eligible.slice(5).map((entry) => entry.member.id));
```

- [ ] **Step 2: Apply row class only to over-limit members**

```tsx
<tr key={member.id} className={overLimitIds.has(member.id) ? "member-overlimit-row" : undefined}>
```

Keep kick/protected logic unchanged.

- [ ] **Step 3: Run focused tests**

Run: `cd frontend && npm test -- src/__tests__/member-table-overlimit.test.tsx src/__tests__/member-actions.test.tsx`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/member-table.tsx frontend/src/__tests__/member-table-overlimit.test.tsx
git commit -m "feat(frontend): highlight active members beyond oldest five"
```

### Task 5: Add minimal CSS for over-limit rows

**Files:**
- Modify: `frontend/src/app/globals.css`

- [ ] **Step 1: Add warning row styles**

```css
.data-table tbody tr.member-overlimit-row {
  background: rgba(255, 125, 135, 0.10);
}

.data-table tbody tr.member-overlimit-row:hover {
  background: rgba(255, 125, 135, 0.14);
  box-shadow: inset 0 1px 0 rgba(255, 125, 135, 0.22);
}
```

- [ ] **Step 2: Run frontend tests for regression**

Run: `cd frontend && npm test -- src/__tests__/member-table-overlimit.test.tsx src/__tests__/member-table-vietnamese.test.tsx src/__tests__/member-actions.test.tsx`
Expected: PASS.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/app/globals.css
git commit -m "style(frontend): add over-limit member row warning tone"
```

## Chunk 3: End-to-end verification and rollout checks

### Task 6: Run required backend + frontend test suites

**Files:**
- Test only (no file edits required)

- [ ] **Step 1: Run backend targeted sync/date tests**

Run: `cd backend && pytest tests/test_workspace_sync.py -v`
Expected: PASS.

- [ ] **Step 2: Run frontend targeted member-table tests**

Run: `cd frontend && npm test -- src/__tests__/member-table-overlimit.test.tsx src/__tests__/member-table-vietnamese.test.tsx src/__tests__/member-actions.test.tsx`
Expected: PASS.

- [ ] **Step 3: Run backend invite-flow regression tests (invite/add-member remains unblocked)**

Run: `cd backend && pytest tests/test_invite_flow.py tests/test_invite_actions.py -v`
Expected: PASS.

- [ ] **Step 4: Run backend member API smoke tests**

Run: `cd backend && pytest tests/test_get_workspace_members.py tests/test_phase12_endpoint_contract.py -v`
Expected: PASS.

- [ ] **Step 5: Commit (if any final test fixes happened)**

```bash
git add <changed-files>
git commit -m "test: stabilize over-limit warning behavior"
```

### Task 7: Manual verification with existing workspaces

**Files:**
- No code changes required; dashboard and API verification

- [ ] **Step 1: Re-sync each workspace in dashboard**

Action:
- Open dashboard.
- Click Sync on `Mitrabisa` and `luluash`.

Expected:
- Sync succeeds for both workspaces.

- [ ] **Step 2: Verify Date added backfill after sync**

Action:
- Call members API for both orgs and inspect `created_at`.

Run examples:
```bash
curl -s http://localhost:8000/api/workspaces/0a066ad8-c17d-457e-ab10-8e10a1b41c3c/members
curl -s http://localhost:8000/api/workspaces/a5bf98fb-b077-4cd5-9c96-32645bde0cde/members
```

Expected:
- `created_at` populated from remote Date added (`created_time`) for active members.

- [ ] **Step 3: Confirm baseline behavior at <=5 active**

Expected:
- `Mitrabisa` (2 active) -> no red rows.
- `luluash` (5 active) -> no red rows.

- [ ] **Step 4: Confirm >5 overflow behavior and unchanged kick/owner protection**

Action:
- Add an active member to a workspace already at 5, then sync.

Expected:
- Only 6th+ active member rows are red.
- Kick still works on eligible member rows.
- Owner row remains protected (still shows protected state and no kick action).

- [ ] **Step 5: Confirm transition back to <=5 clears warning**

Action:
- Kick one highlighted overflow member to return to 5 active members.

Expected:
- Red highlight clears for that workspace once active members are back to 5.

- [ ] **Step 6: Final commit for any manual-fix changes**

```bash
git add <changed-files>
git commit -m "chore: finalize member over-limit warning rollout"
```

## References for implementer

- Spec: `docs/superpowers/specs/2026-03-10-member-overlimit-warning-design.md`
- Backend sync logic: `backend/app/routers/workspaces.py`
- Backend sync tests: `backend/tests/test_workspace_sync.py`
- Member table component: `frontend/src/components/member-table.tsx`
- Styles: `frontend/src/app/globals.css`
- Existing member tests: `frontend/src/__tests__/member-actions.test.tsx`, `frontend/src/__tests__/member-table-vietnamese.test.tsx`
