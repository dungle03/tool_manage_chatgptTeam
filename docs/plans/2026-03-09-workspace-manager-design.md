# ChatGPT Workspace Manager - Design Document

Date: 2026-03-09
Status: Approved

## 1) Goal
Build one unified dashboard to manage multiple ChatGPT Team workspaces with:
- Team/workspace overview
- Per-team member list (name, email, join date)
- Member status visibility
- Kick member action
- Add new team source for management
- Basic invite flow

This design intentionally keeps v1 focused and aligned with `plan.md` backend API contract.

---

## 2) Scope (v1)
### In scope
- Single dashboard page for multi-team management
- Auto-sync team/workspace list from upstream API source
- Team card + member table per team
- Member fields: name, email, role, join date, status
- Kick member with confirmation
- Basic invite (single email)
- Invite list view and basic invite operations (resend/cancel)
- Action/audit logging for sync, invite, kick

### Out of scope (v1)
- Redeem code system
- Bulk invite workflows
- Advanced automation jobs (auto-kick, auto-resend)
- Analytics/billing extras

---

## 3) UX / Information Architecture
## 3.1 Unified dashboard
- Top summary strip:
  - Total teams
  - Total members
  - Pending invites
  - Sync errors
- Team list (cards or expandable sections):
  - Team name
  - Team status (`syncing | synced | error`)
  - Member usage (members / limit if available)
  - Last sync timestamp
  - Expand to member table

## 3.2 Member table (inside each team)
Columns:
- Name
- Email
- Join Date
- Role
- Status
- Action (Kick)

Member status set for v1 (confirmed):
- `active`
- `invited`
- `pending`
- `removed`
- `error`

## 3.3 Actions
- Add Team: connect new team source, then sync
- Invite member (basic): email + role
- Kick member: confirmation modal before execution
- Invite management: list invites, resend invite, cancel invite

---

## 4) Backend API Contract (fixed by user request)
Backend API must follow `plan.md` section 7 exactly:

### Workspace
- `GET /api/workspaces`
- `GET /api/workspaces/{id}/members`

### Members
- `POST /api/invite`
- `DELETE /api/member`

### Invites
- `GET /api/invites`
- `POST /api/resend-invite`
- `DELETE /api/cancel-invite`

Notes:
- Naming and route shapes above are preserved as the source of truth for v1.
- Dashboard and frontend must map all UI actions to these seven endpoints.

---

## 5) Data Model (v1)
Based on `plan.md` with only required fields for current scope:

### `workspaces`
- `id`
- `org_id`
- `name`
- `member_limit`
- `created_at`

### `members`
- `id`
- `org_id`
- `email`
- `name`
- `role`
- `status`
- `invite_date`

### `invites`
- `id`
- `org_id`
- `email`
- `invite_id`
- `status`
- `created_at`

Optional later table (not required in v1 flow):
- `redeem_codes`

---

## 6) Data Flow
1. Dashboard load:
   - Call `GET /api/workspaces`
   - Render team summary blocks
2. Team expand/open:
   - Call `GET /api/workspaces/{id}/members`
   - Render member table
3. Invite member:
   - Call `POST /api/invite`
   - Refresh team member and invite state
4. Kick member:
   - Confirm in UI
   - Call `DELETE /api/member`
   - Optimistic or post-success refresh
5. Invite management:
   - Call `GET /api/invites`
   - Resend via `POST /api/resend-invite`
   - Cancel via `DELETE /api/cancel-invite`

---

## 7) Safety & Error Handling
- Never expose upstream session token in frontend
- Backend-only credential usage
- Guard UI against duplicate submit (disable button while pending)
- Standardized error payload for all endpoints
- Retry path for transient failures
- Permission failures surfaced with explicit message

Kick safeguards:
- Explicit confirmation dialog
- Clear display of target email + workspace before submit

---

## 8) Test Scenarios (v1)
1. Dashboard loads all workspaces successfully
2. Per-workspace member list shows required columns
3. Invite member success/failure states are visible
4. Kick member success updates status/list correctly
5. Invite list renders pending invites accurately
6. Resend invite updates state and logs action
7. Cancel invite removes/updates invite row correctly
8. API error states show actionable messages in UI

---

## 9) Tech Baseline
- Frontend: Next.js + TailwindCSS + shadcn/ui
- Backend: FastAPI or NestJS (implementation choice later)
- DB: PostgreSQL
- Deployment: Docker Compose

---

## 10) Final Decisions Captured
- Single unified dashboard
- Multi-team visibility with per-team member table
- Required member fields: name, email, join date
- Kick action + related statuses
- Basic invite retained
- Backend API contract locked to `plan.md` section 7 (7 endpoints)

This design is now ready for implementation planning.