# ChatGPT Workspace Manager - Development Plan

## 1. Project Overview

Build a web dashboard to manage multiple ChatGPT Team workspaces,
including:

-   View workspace members
-   Invite new members
-   Remove members
-   View pending invites
-   Track workspace capacity
-   Manage multiple workspaces in one dashboard

The tool will interact with ChatGPT internal workspace APIs.

------------------------------------------------------------------------

# 2. System Architecture

Frontend\
→ Dashboard UI (React / Next.js)

Backend\
→ API server (FastAPI or Node.js)

Database\
→ Store workspace metadata, invites, codes

ChatGPT API\
→ Internal endpoints used by the ChatGPT web interface

Architecture Diagram

Frontend\
↓\
Backend API\
↓\
ChatGPT Internal API

------------------------------------------------------------------------

# 3. Core Features

## Workspace Management

-   List all workspaces
-   Show workspace capacity (members / limit)
-   Show workspace status

Example

  Workspace Name   Members   Capacity
  ---------------- --------- ----------
  Workspace A      4         7
  Workspace B      5         7

------------------------------------------------------------------------

## Member Management

Features

-   List members
-   Show role (Owner / Member)
-   Show invite date
-   Remove member
-   Approve invite

Fields

-   Email
-   Account Name
-   Role
-   Invite Date
-   Status

Status Types

active\
pending\
invited

------------------------------------------------------------------------

## Invite System

Allow admin to invite users to workspace.

Actions

Invite user by email\
Bulk invite users\
View pending invites\
Resend invite\
Cancel invite

------------------------------------------------------------------------

## Redeem Code System (Optional)

For automated onboarding.

Flow

Admin generates invite code\
User submits code + email\
System auto-invites user

Database table

redeem_codes

Fields

id\
code\
used\
used_by\
expire_time

------------------------------------------------------------------------

# 4. ChatGPT Internal APIs

## Get Workspaces

GET

/backend-api/accounts

Response

accounts\[\]

Fields

id\
name

------------------------------------------------------------------------

## Get Members

GET

/backend-api/organizations/{org_id}/members

Response

members\[\]

Fields

email\
name\
role\
status

------------------------------------------------------------------------

## Invite Member

POST

/backend-api/organizations/{org_id}/invites

Body

email\
role

------------------------------------------------------------------------

## Remove Member

DELETE

/backend-api/organizations/{org_id}/members/{member_id}

------------------------------------------------------------------------

## List Invites

GET

/backend-api/organizations/{org_id}/invites

------------------------------------------------------------------------

# 5. Authentication

Use ChatGPT session token.

Sources

https://chatgpt.com/api/auth/session

Token fields

accessToken

Or use cookie

\_\_Secure-next-auth.session-token

Headers

Authorization: Bearer `<token>`{=html}

------------------------------------------------------------------------

# 6. Database Design

Recommended: PostgreSQL

Tables

## workspaces

id\
org_id\
name\
member_limit\
created_at

------------------------------------------------------------------------

## members

id\
org_id\
email\
name\
role\
status\
invite_date

------------------------------------------------------------------------

## invites

id\
org_id\
email\
invite_id\
status\
created_at

------------------------------------------------------------------------

## redeem_codes

id\
code\
used\
used_by\
expire_time

------------------------------------------------------------------------

# 7. Backend API Design

## Workspace

GET /api/workspaces\
GET /api/workspaces/{id}/members

------------------------------------------------------------------------

## Members

POST /api/invite\
DELETE /api/member

------------------------------------------------------------------------

## Invites

GET /api/invites\
POST /api/resend-invite\
DELETE /api/cancel-invite

------------------------------------------------------------------------

# 8. Frontend UI Pages

## Dashboard

Show

Workspace cards\
Member usage\
Status indicator

------------------------------------------------------------------------

## Workspace Detail Page

Show

Members table\
Pending invites\
Actions

Invite\
Remove\
Approve

------------------------------------------------------------------------

## Invite Modal

Input

Email address

Buttons

Send Invite\
Bulk Invite

------------------------------------------------------------------------

# 9. UI Components

Workspace Card\
Members Table\
Invite Modal\
Redeem Code Panel\
Admin Settings

------------------------------------------------------------------------

# 10. Background Jobs

Auto refresh member list every 30 seconds

Optional

Auto remove inactive members\
Auto resend failed invites

------------------------------------------------------------------------

# 11. Tech Stack

Frontend

Next.js\
TailwindCSS\
Shadcn UI

Backend

FastAPI or NestJS

Database

PostgreSQL

Cache

Redis (optional)

------------------------------------------------------------------------

# 12. Security Considerations

Protect admin dashboard

Add

Admin login\
API rate limits\
Token encryption

Never expose ChatGPT session tokens publicly.

------------------------------------------------------------------------

# 13. Deployment

Docker recommended

Services

Frontend container\
Backend container\
Database container

Example

docker compose up -d

------------------------------------------------------------------------

# 14. Estimated Development Time

Backend API\
\~4 hours

Frontend Dashboard\
\~6 hours

Integration\
\~2 hours

Total

\~12 hours

------------------------------------------------------------------------

# 15. Future Improvements

Add multi-admin support

Add analytics dashboard

Add billing / slot tracking

Add Telegram / Discord notification

------------------------------------------------------------------------

END
