# Member over-limit warning design

## Context
User wants dashboard-only warning behavior for ChatGPT Team member management:
- Team baseline is 5 members.
- Keep the 5 oldest active members as "old users".
- Any active member beyond that (6th+) should be highlighted red to make kick actions easier.
- Do not block adding members.
- Do not count pending invites.
- Source of truth for Date added should match ChatGPT Admin members page behavior.

## Confirmed findings from current code and data
- Current sync logic stores member date from `created` / `created_at` only, so local DB currently has `members.created_at = NULL` for existing teams.
- Direct remote verification against ChatGPT members API for existing teams shows date-like field is `created_time` (present for all sampled members).
- Therefore, Date added should be mapped from `created_time`.

## Goals
1. Correctly persist Date added for members from ChatGPT API.
2. Compute over-limit members based on oldest 5 active members.
3. Visually highlight only over-limit member rows in the Members table.
4. Keep behavior simple, predictable, and focused on kick workflow.

## Non-goals
- No invite blocking logic.
- No workspace-wide red card mode.
- No redesign of member management architecture.

## Design decisions

### 1) Date added source
- Extraction priority for member Date added: `created_time` (primary) -> `created_at` (legacy fallback) -> `created` (legacy fallback).
- Parse contract:
  - If value is ISO datetime string (e.g. `2026-03-10T10:05:08.547522Z`), parse and normalize to UTC.
  - If value is epoch seconds or milliseconds, convert to UTC datetime.
  - If parsing fails, store `NULL` and treat as unknown-date member.
- Persist parsed value into `members.created_at`.
- Keep `invite_date` unchanged unless needed by existing compatibility code.

### 2) Over-limit classification rule
For each workspace member list render:
1. Consider only active members (`status` compared case-insensitively to `active`).
2. Members with unknown Date added (`created_at = NULL`) are excluded from over-limit highlighting until timestamp exists.
3. Sort active members with known `created_at` by:
   - `created_at` ascending (oldest first),
   - then `remote_id` ascending,
   - then local `id` ascending.
4. First 5 active members in this deterministic order are baseline old users.
5. Any active member after index 4 is marked as over-limit.
6. Members not active are excluded from quota logic.
7. Pending invites are excluded from quota logic.

### 3) UI behavior
- Add red highlight only to over-limit rows in `MemberTable`.
- Keep kick button behavior unchanged.
- Keep owner protection behavior unchanged.
- If active members <= 5, no row is highlighted.

### 4) Handling missing date values
- Expected steady state after sync: `created_at` populated from `created_time`.
- Required fallback behavior: active members with `created_at = NULL` stay unhighlighted (unknown-date) and are excluded from 5-vs-6 classification.
- Given current confirmed API payload includes `created_time`, missing-date handling is low-probability but still deterministic.

## Data flow
1. User triggers sync (or sync runs via existing flow).
2. Backend fetches members from ChatGPT API.
3. Backend maps `created_time` into `members.created_at`.
4. Frontend loads members list.
5. MemberTable computes over-limit set from active members sorted by date.
6. Table renders red style for 6th+ active members.

## Files expected to change
- `backend/app/routers/workspaces.py`
  - Update member date extraction to include `created_time` with legacy fallbacks.
- `frontend/src/components/member-table.tsx`
  - Add over-limit computation and row class application.
- `frontend/src/app/globals.css`
  - Add styles for over-limit rows.
- Required tests:
  - backend sync mapping test covering `created_time` primary and `created_at`/`created` fallbacks.
  - frontend member-table test covering active-only counting, pending excluded, <=5 no highlight, 6th+ highlight, deterministic tie-breaks, and unknown-date behavior.

## Acceptance criteria
1. Date added extraction uses priority: `created_time` -> `created_at` -> `created`, persisted to `members.created_at` in UTC.
2. Only active members count toward 5-member baseline (case-insensitive status match on `active`).
3. Oldest 5 active members (deterministic sort by `created_at`, then `remote_id`, then `id`) are not highlighted.
4. Active members from 6th onward are highlighted red in member rows.
5. Pending invites do not affect over-limit highlighting.
6. Members with unknown Date added (`created_at = NULL`) remain unhighlighted and excluded from 5-vs-6 classification.
7. Invite/add-member flow remains unblocked.
8. Kick behavior and owner protection behavior remain unchanged.
9. When team returns to <=5 active members, highlight is removed accordingly.
10. For equal timestamps, tie-break rules produce stable highlight results across re-renders.

## Risks and mitigations
- Risk: Existing rows with NULL created_at from past syncs.
  - Mitigation: Re-sync workspace once after deployment to populate created_at from created_time.
- Risk: Future upstream payload shape changes.
  - Mitigation: Keep date extraction tolerant (`created_time` primary, legacy fields as fallback).

## Rollout notes
- No migration required for schema.
- Recommended post-change action: run sync for each workspace to backfill Date added.
