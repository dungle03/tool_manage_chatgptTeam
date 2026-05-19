# Plan: Personal ChatGPT Accounts OAuth

Created: 2026-05-19 02:26 +07:00
Status: ✅ Complete

## Overview

Add a separate **Personal Accounts** area to the existing ChatGPT Team Manager.

The feature lets the user add personal ChatGPT accounts through OAuth, stores tokens internally, refreshes tokens safely, and tracks account status as **Live**, **Die**, or **Need re-login**.

Team Workspace management remains unchanged and isolated.

## Product Goals

- Track personal ChatGPT account health.
- Avoid exposing tokens in the UI.
- Use OAuth-only account adding.
- Refresh tokens automatically and safely.
- Keep Team and Personal account data separate.

## Non-Goals

- No manual token paste fallback.
- No token viewing/copying in UI.
- No personal account API/chat usage in MVP.
- No linking Personal accounts to Team workspaces in MVP.

## Tech Stack

- Frontend: Next.js / React / TypeScript
- Backend: FastAPI / Python
- Database: SQLite via SQLAlchemy
- Auth Integration: ChatGPT/Codex-style OAuth, experimental

## Key Decisions

- UI button label: `Add Personal ChatGPT Account`
- OAuth callback mode: local callback auto flow
- Duplicate email: ask user before overwrite/create-new/cancel
- Refresh failure: mark `Need re-login`, keep card, show `Reconnect`
- Token storage: backend/database only, masked/not displayed in frontend
- Refresh pattern: use single-flight lock per account, based on 9router behavior

## Status Model

| Status        | Meaning                                             |
| ------------- | --------------------------------------------------- |
| Live          | Token refresh/check succeeded recently              |
| Die           | Account check confirms invalid/unusable state       |
| Need re-login | OAuth refresh is unrecoverable; user must reconnect |
| Unknown       | Account exists but has not been checked yet         |

## Phases

| Phase | Name                                |      Status | Progress |
| ----- | ----------------------------------- | ----------: | -------: |
| 01    | Discovery and Safety Baseline       | ✅ Complete |     100% |
| 02    | Data Model and Migration            | ✅ Complete |     100% |
| 03    | OAuth Flow Backend                  | ✅ Complete |     100% |
| 04    | Refresh and Account Health Service  | ✅ Complete |     100% |
| 05    | Personal Accounts API               | ✅ Complete |     100% |
| 06    | Frontend Personal Accounts Tab      | ✅ Complete |     100% |
| 07    | Integration, Testing, and Hardening | ✅ Complete |     100% |

## Quick Commands

- Detailed design: `/design`
- Start implementation: `/code phase-01`
- Check next step: `/next`
- Save context: `/save-brain`

## Risk Register

| Risk                            | Impact                      | Mitigation                                                                |
| ------------------------------- | --------------------------- | ------------------------------------------------------------------------- |
| Codex OAuth changes upstream    | Add/reconnect may break     | Gate as experimental; clear UI errors                                     |
| Rotating refresh token reused   | Token family can be revoked | Single-flight refresh lock; no blind retry                                |
| Token leak in logs/UI           | Account compromise          | Mask tokens; redact logs; never serialize token to frontend               |
| Team tab regression             | Existing app breakage       | Keep separate router/service/table; no changes to team `get_account_info` |
| Duplicate accounts confuse user | Wrong account overwritten   | Confirmation modal before overwrite/create-new                            |

## Acceptance Summary

- User can add account by OAuth.
- Account appears in Personal Accounts tab.
- Token values are never shown in UI.
- Duplicate email asks for user decision.
- Manual refresh/check updates status.
- Refresh unrecoverable error marks `Need re-login`.
- Existing Team tab behavior is unchanged.
