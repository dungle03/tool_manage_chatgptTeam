# ChatGPT Workspace Manager

[🇻🇳 Tiếng Việt](./README.md) | [🇺🇸 English](./README.en.md)

**ChatGPT Workspace Manager** là dashboard vận hành nội bộ giúp quản lý nhiều **ChatGPT Team workspaces** và **ChatGPT Personal accounts** trong một giao diện duy nhất.

Project kết hợp **FastAPI backend**, **Next.js frontend**, **SQLite database**, background worker và realtime updates để hỗ trợ các tác vụ quản trị thường gặp: import team, đồng bộ member/invite, kiểm tra trạng thái subscription, refresh token, theo dõi account cá nhân Plus, và tự động cập nhật dữ liệu nền.

---

## Mục lục

- [Tổng quan](#tổng-quan)
- [Chương trình làm gì?](#chương-trình-làm-gì)
- [Tính năng chính](#tính-năng-chính)
- [Kiến trúc hệ thống](#kiến-trúc-hệ-thống)
- [Cấu trúc repository](#cấu-trúc-repository)
- [Tech stack](#tech-stack)
- [Quick Start](#quick-start)
- [Biến môi trường](#biến-môi-trường)
- [API chính](#api-chính)
- [Database model](#database-model)
- [Kiểm tra chất lượng](#kiểm-tra-chất-lượng)
- [Ghi chú vận hành](#ghi-chú-vận-hành)
- [Giới hạn hiện tại](#giới-hạn-hiện-tại)
- [Security notice](#security-notice)

---

## Tổng quan

Khi phải vận hành nhiều ChatGPT Team workspace hoặc nhiều tài khoản ChatGPT cá nhân, việc kiểm tra thủ công từng workspace/account rất mất thời gian và dễ lệch dữ liệu.

Project này gom các tác vụ đó vào một dashboard:

- theo dõi nhiều workspace Team cùng lúc
- xem member, invite, seat usage và expiry date
- xử lý member/invite từ một nơi
- phát hiện member không hợp lệ so với local state
- quản lý personal accounts đã OAuth vào tool
- kiểm tra gói Plus/plan renewal của personal accounts
- tự động sync dữ liệu định kỳ trong background
- cập nhật UI gần realtime cho workspace events

Codebase phù hợp nhất cho:

- công cụ nội bộ
- vận hành local hoặc single-instance deployment
- dashboard admin cho môi trường kiểm soát tốt
- workflow cần tự động hóa sync/token refresh nhưng vẫn có nút thao tác thủ công

---

## Chương trình làm gì?

Ở mức cao, chương trình đóng vai trò như một **control panel** cho ChatGPT Team và Personal accounts.

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

### Với ChatGPT Team workspace

Tool cho phép import workspace bằng token, lưu metadata vào local database, đồng bộ member/invite từ upstream, theo dõi ngày hết hạn team, refresh token nền và thực hiện các thao tác quản trị như kick member, tạo/resend/cancel invite.

### Với ChatGPT Personal account

Tool cho phép thêm tài khoản cá nhân thông qua OAuth, lưu token, kiểm tra health, refresh token, đọc entitlement data để xác định account đang dùng plan nào và ngày Plus renew/expire là khi nào.

### Với background sync

Backend có worker chạy nền để:

- refresh token cho workspace/account khi đến hạn
- sync workspace stale/hot theo scheduler
- sync plan entitlement cho personal accounts theo batch
- tránh gọi upstream quá dồn dập bằng batch size và delay giữa account
- lưu lỗi sync riêng để dashboard hiển thị được trạng thái vận hành

---

## Tính năng chính

### 1. Quản lý ChatGPT Team workspaces

- Import workspace/team bằng `access_token`
- Hiển thị danh sách workspace trong dashboard thống nhất
- Theo dõi:
  - team name
  - organization ID
  - seat usage
  - member count
  - pending invite count
  - sync status
  - billing/expiry date
  - token health và refresh status
  - last sync / next sync / error state
- Xem workspace details gồm member, invite và unauthorized findings
- Trigger manual sync cho từng workspace
- Trigger manual **Refresh Token** cho từng workspace
- Tự động refresh token Team khi token gần hết hạn hoặc đến lịch xử lý
- Cập nhật token thủ công khi cần thay access token
- Đổi tên workspace trong local dashboard
- Cấu hình unauthorized policy theo từng workspace
- Xóa workspace khỏi local database
- Background scheduler tự xử lý stale workspace và hot workspace

### 2. Quản lý members

- Xem danh sách member theo workspace
- Hiển thị tên, email, role và thời gian join
- Kick member với confirmation flow
- Persist member snapshot trong local SQLite
- Highlight các tình huống vượt seat limit hoặc state bất thường

### 3. Quản lý invites

- Tạo invite mới bằng email
- Resend pending invite
- Cancel pending invite
- Theo dõi pending invite theo từng workspace
- Xử lý an toàn trường hợp upstream trả `invite_id` trùng
- Đồng bộ invite state về local database

### 4. Unauthorized member detection

- Phát hiện member tồn tại trên upstream nhưng không có trong local state/whitelist
- Hỗ trợ manual review và `auto_kick`
- Lưu lịch sử finding:
  - first seen
  - last seen
  - status
  - action reason
  - resolved timestamp
- Tự động resolve finding khi trạng thái đã đồng bộ lại

### 5. Team token refresh và workspace sync nền

Đây là một phần quan trọng của tool, dùng để giữ workspace Team hoạt động ổn định mà không phải thay token thủ công liên tục.

- Backend có service refresh token riêng cho workspace Team
- Luồng này **không tự đăng nhập trực tiếp trong dashboard**; nó gọi tool/token provider đã cấu hình sẵn để tự động đăng nhập ChatGPT và lấy access token mới
- Có endpoint manual refresh token: `POST /api/workspaces/{id}/refresh-token`
- Manual refresh chạy bằng background task, API trả về `accepted` hoặc `in_progress`
- Có lock theo workspace để tránh refresh trùng
- Sau khi tool lấy được token mới, backend verify token đó đúng workspace/org trước khi mark success
- Token mới, thời gian refresh và error state được persist vào database
- Sau refresh thành công, backend chạy follow-up sync workspace để cập nhật member/invite/summary
- Nếu refresh lỗi, backend lưu failure state và phát event lỗi về dashboard
- Auto token refresh cycle chạy trong background worker
- Auto refresh chọn workspace đến hạn theo metadata trong database
- Có giới hạn số refresh chạy song song và delay giữa batch
- SSE phát các event:
  - `workspace_token_refreshed`
  - `workspace_token_refresh_failed`
- Scheduler có hot-window và follow-up sync sau các action quan trọng
- Có retry steps khi sync lỗi
- Giới hạn số workspace sync song song
- SSE đẩy workspace updates lên dashboard gần realtime

Yêu cầu quan trọng của Team Refresh Token:

- Cần có **tool tự động đăng nhập/lấy token** đã hoạt động sẵn trong môi trường chạy backend
- Tool đó chịu trách nhiệm mở/login ChatGPT, vượt các bước cần thiết và xuất token mới theo format backend đọc được
- Backend chỉ điều phối refresh, gọi tool lấy token, verify token, lưu DB và sync lại workspace
- Nếu token-provider tool lỗi, bị Cloudflare chặn, sai account hoặc không trả token hợp lệ, refresh sẽ bị mark failed và dashboard hiển thị lỗi

### 6. Workspace maintenance tools

- Update access token thủ công cho workspace qua dashboard/API
- Rename workspace trong local dashboard
- Xem workspace details dạng tổng hợp:
  - workspace summary
  - members
  - invites
  - unauthorized findings
- Cấu hình unauthorized member mode:
  - manual review
  - auto-kick
- Trust unauthorized finding khi xác nhận member hợp lệ
- Kick unauthorized finding trực tiếp từ finding record
- Global unauthorized findings view để xem vấn đề trên toàn bộ workspace

### 7. Personal Accounts dashboard

- Thêm ChatGPT Personal account qua OAuth
- Hiển thị trạng thái account:
  - `live`
  - `die`
  - `need_relogin`
  - `unknown`
- Hiển thị email, tên account, token expiry và trạng thái OAuth
- Check health từng account
- Refresh token từng account
- Reconnect OAuth khi token/account cần login lại
- Xóa account khỏi local database

### 8. Personal Plus entitlement tracking

Tool có thể đọc entitlement data của personal account để lưu và hiển thị:

- `subscription_plan`
- `plan_expires_at`
- `plan_renews_at`
- `last_plan_sync_at`
- `next_plan_sync_at`
- `plan_sync_error`
- `plan_sync_fail_count`

Trên dashboard, account card hiển thị ngày **Plus renews** và modal quản lý hiển thị chi tiết lịch sync/lỗi sync.

### 9. Personal Plan Auto Sync

Để không phải bấm check từng account khi có nhiều tài khoản cá nhân, backend có service sync nền riêng cho personal accounts.

Cơ chế:

- chọn account active, có access token, không ở trạng thái `need_relogin`
- chỉ sync account đến hạn theo `next_plan_sync_at`
- giới hạn batch size mỗi vòng
- delay giữa từng account để giảm rủi ro rate-limit/Cloudflare block
- lock theo account để tránh sync trùng khi background và manual action chạy cùng lúc
- nếu token lỗi auth, thử refresh token rồi sync lại
- nếu lỗi tạm thời, lưu `plan_sync_error` và retry sau

Nút **Sync Plans** trên UI gọi batch sync thủ công, còn background worker tự sync theo lịch.

### 10. Realtime và UI refresh

- Workspace updates được đẩy qua SSE
- Frontend dedupe event/toast để giảm nhiễu
- Personal Accounts dashboard có cơ chế silent refresh định kỳ để bắt dữ liệu mới từ background sync
- Các nút manual action đều reload lại dữ liệu sau khi backend commit

### 11. Export dữ liệu

Có tool Python độc lập để export workspace/member data từ local database:

```text
backend/export_workspace_members.py
```

Hỗ trợ export team/member phục vụ audit hoặc reporting.

---

## Kiến trúc hệ thống

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

### Runtime flow chính

1. Người dùng thao tác trên Next.js dashboard.
2. Frontend gọi FastAPI endpoints.
3. Backend gọi upstream ChatGPT APIs khi cần.
4. Backend lưu state vào SQLite.
5. Background worker chạy token refresh và sync theo lịch.
6. Workspace changes được phát qua SSE.
7. Frontend cập nhật dashboard bằng SSE, reload thủ công hoặc polling nhẹ.

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
Sleep theo SYNC_LOOP_INTERVAL_SECONDS
```

---

## Cấu trúc repository

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
│  └─ SYNC_RUNBOOK.md             # Runbook cho sync/realtime debugging
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

## Tech stack

| Tầng            | Công nghệ                             |
| --------------- | ------------------------------------- |
| Frontend        | Next.js 14, React 18, TypeScript      |
| Styling         | Vanilla CSS                           |
| Backend         | FastAPI, SQLAlchemy, Pydantic         |
| Database        | SQLite mặc định                       |
| Realtime        | Server-Sent Events                    |
| Background jobs | Asyncio worker trong FastAPI lifespan |
| Backend tests   | pytest                                |
| Frontend tests  | Vitest, Testing Library               |
| Runtime scripts | PowerShell                            |

### Yêu cầu runtime

- **Python**: khuyến nghị 3.11+
- **Node.js**: `>= 22.12.0`
- **OS**: project hiện được tối ưu cho Windows/local PowerShell workflow

---

## Quick Start

### Cách nhanh nhất

Từ root repository:

```powershell
.\start_dashboard.ps1
```

Script này dùng workflow local hiện có để chạy dashboard/backend theo cấu hình project.

### Cài backend thủ công

```powershell
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Chạy backend từ thư mục `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Cài frontend thủ công

Chạy từ thư mục `frontend/`:

```powershell
npm install
npm run dev
```

Mở dashboard:

```text
http://localhost:3000
```

---

## Biến môi trường

Project hiện dùng file `.env` ở root cho local runtime. Một số deployment cũng có thể dùng `backend/.env` hoặc `frontend/.env.local` tùy cách chạy script.

### Core backend

| Biến                                        | Mặc định                                     | Mục đích                                 |
| ------------------------------------------- | -------------------------------------------- | ---------------------------------------- |
| `DATABASE_URL`                              | `backend/workspace_manager.db` nếu không set | Chuỗi kết nối database                   |
| `ADMIN_TOKEN`                               | rỗng                                         | Token bảo vệ admin endpoints             |
| `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC` | rỗng                                         | Tắt background sync khi test/chạy cô lập |

### Workspace sync

| Biến                           | Mặc định     | Mục đích                                 |
| ------------------------------ | ------------ | ---------------------------------------- |
| `SYNC_LOOP_INTERVAL_SECONDS`   | `5`          | Chu kỳ vòng background chính             |
| `SYNC_STALE_MINUTES`           | `5`          | Ngưỡng workspace stale                   |
| `SYNC_PENDING_INVITE_SECONDS`  | `15`         | Tăng tần suất sync khi có pending invite |
| `SYNC_BASELINE_MINUTES`        | `5`          | Chu kỳ refresh nền cơ bản                |
| `SYNC_HOT_WINDOW_SECONDS`      | `180`        | Thời gian workspace ở trạng thái hot     |
| `SYNC_FOLLOWUP_STEPS`          | `5,15,30,60` | Các mốc follow-up sync sau action        |
| `SYNC_ERROR_RETRY_STEPS`       | `10,30,60`   | Retry checkpoints sau lỗi sync           |
| `SYNC_MAX_PARALLEL_WORKSPACES` | `2`          | Số workspace sync song song tối đa       |

### Personal account OAuth

| Biến                                | Mục đích                          |
| ----------------------------------- | --------------------------------- |
| `ENABLE_EXPERIMENTAL_CHATGPT_OAUTH` | Bật luồng OAuth personal accounts |
| `CHATGPT_OAUTH_CLIENT_ID`           | OAuth client ID                   |
| `CHATGPT_OAUTH_AUTH_URL`            | OAuth authorization URL           |
| `CHATGPT_OAUTH_TOKEN_URL`           | OAuth token URL                   |
| `CHATGPT_OAUTH_REDIRECT_URI`        | Redirect URI local                |
| `CHATGPT_OAUTH_SCOPE`               | OAuth scopes                      |

### Personal Plan Auto Sync

| Biến                               | Mặc định | Mục đích                                             |
| ---------------------------------- | -------- | ---------------------------------------------------- |
| `PERSONAL_PLAN_SYNC_STALE_HOURS`   | `6`      | Sau bao lâu account cần sync plan lại                |
| `PERSONAL_PLAN_SYNC_BATCH_SIZE`    | `5`      | Số personal accounts sync tối đa mỗi vòng background |
| `PERSONAL_PLAN_SYNC_DELAY_SECONDS` | `2`      | Delay giữa mỗi account khi sync batch                |
| `PERSONAL_PLAN_SYNC_RETRY_MINUTES` | `45`     | Sau lỗi tạm thời thì retry sau bao lâu               |

Cấu hình khuyến nghị khi có nhiều personal accounts:

```env
SYNC_LOOP_INTERVAL_SECONDS=30
PERSONAL_PLAN_SYNC_STALE_HOURS=6
PERSONAL_PLAN_SYNC_BATCH_SIZE=3
PERSONAL_PLAN_SYNC_DELAY_SECONDS=5
PERSONAL_PLAN_SYNC_RETRY_MINUTES=45
```

### Frontend

| Biến                      | Mục đích                        |
| ------------------------- | ------------------------------- |
| `NEXT_PUBLIC_ADMIN_TOKEN` | Token frontend gửi sang backend |

---

## API chính

### Workspace APIs

| Method   | Endpoint                                                       | Mô tả                                                  |
| -------- | -------------------------------------------------------------- | ------------------------------------------------------ |
| `GET`    | `/api/workspaces`                                              | Lấy danh sách workspace đang quản lý                   |
| `POST`   | `/api/teams/import`                                            | Import workspace/team từ token                         |
| `GET`    | `/api/workspaces/{id}/details`                                 | Lấy summary, members, invites và unauthorized findings |
| `GET`    | `/api/workspaces/{id}/members`                                 | Lấy danh sách member của workspace                     |
| `POST`   | `/api/workspaces/{id}/sync`                                    | Trigger sync workspace ngay lập tức                    |
| `POST`   | `/api/workspaces/{id}/refresh-token`                           | Trigger refresh token workspace bằng background task   |
| `PATCH`  | `/api/workspaces/{id}/token`                                   | Cập nhật access token thủ công cho workspace           |
| `PATCH`  | `/api/workspaces/{id}/name`                                    | Đổi tên workspace trong local dashboard                |
| `PATCH`  | `/api/workspaces/{id}/unauthorized-policy`                     | Đổi chế độ xử lý unauthorized member                   |
| `GET`    | `/api/workspaces/{id}/unauthorized-members`                    | Lấy unauthorized findings của một workspace            |
| `POST`   | `/api/workspaces/{id}/unauthorized-members/{finding_id}/trust` | Trust một unauthorized finding                         |
| `POST`   | `/api/workspaces/{id}/unauthorized-members/{finding_id}/kick`  | Kick member từ unauthorized finding                    |
| `GET`    | `/api/unauthorized-findings`                                   | Lấy toàn bộ unauthorized findings                      |
| `DELETE` | `/api/workspaces/{id}`                                         | Xóa workspace khỏi local database                      |
| `GET`    | `/api/events/workspaces`                                       | Mở SSE stream cho workspace events                     |

### Member / Invite APIs

| Method   | Endpoint                  | Mô tả                              |
| -------- | ------------------------- | ---------------------------------- |
| `DELETE` | `/api/member`             | Kick member khỏi workspace         |
| `POST`   | `/api/invite`             | Tạo invite mới                     |
| `POST`   | `/api/resend-invite`      | Gửi lại invite đang chờ            |
| `DELETE` | `/api/cancel-invite`      | Hủy invite đang chờ                |
| `GET`    | `/api/invites?org_id=...` | Lấy danh sách invite của workspace |

### Personal Account APIs

| Method   | Endpoint                                | Mô tả                                             |
| -------- | --------------------------------------- | ------------------------------------------------- |
| `GET`    | `/api/personal-accounts`                | Lấy danh sách personal accounts                   |
| `GET`    | `/api/personal-accounts/{id}`           | Lấy chi tiết personal account                     |
| `POST`   | `/api/personal-accounts/{id}/check`     | Check health và sync plan cho một account         |
| `POST`   | `/api/personal-accounts/{id}/refresh`   | Refresh token cho một account                     |
| `POST`   | `/api/personal-accounts/{id}/reconnect` | Tạo OAuth reconnect URL                           |
| `POST`   | `/api/personal-accounts/sync`           | Batch sync plan entitlement cho personal accounts |
| `DELETE` | `/api/personal-accounts/{id}`           | Xóa personal account khỏi local database          |

Ví dụ manual sync personal plans:

```text
POST /api/personal-accounts/sync?limit=10&force=true
```

---

## Database model

### `workspaces`

Lưu trạng thái vận hành của từng ChatGPT Team workspace:

- tên team
- org/account ID
- access token
- ngày hết hạn/billing cycle
- metadata sync/scheduler
- token refresh status
- error state

### `members`

Lưu snapshot member theo từng workspace:

- remote member ID
- tên
- email
- role
- thời gian join

### `invites`

Lưu trạng thái invite:

- email
- invite ID
- pending status
- cờ đánh dấu invite do tool tạo
- trạng thái sync local/upstream

### `unauthorized_findings`

Lưu lịch sử phát hiện và xử lý unauthorized member:

- remote ID
- email
- role
- current status
- action reason
- first seen / last seen / resolved timestamps

### `personal_accounts`

Lưu ChatGPT Personal accounts đã thêm vào tool:

- email/name/avatar
- OAuth token và refresh token metadata
- token expiry/refresh schedule
- account status
- subscription plan
- Plus renew/expire date
- plan sync schedule
- plan sync error/fail count

---

## Export dữ liệu team và member

Tool export độc lập:

```text
backend/export_workspace_members.py
```

Ví dụ chạy từ thư mục `backend/`:

```powershell
python export_workspace_members.py --format csv --output exports/team_members_export.csv --include-empty-teams
```

Các cột export chính:

- `team_name`
- `team_id`
- `team_expires_at`
- `member_name`
- `member_email`
- `member_role`
- `member_joined_at`

---

## Kiểm tra chất lượng

### Lệnh tổng hợp

Từ root repository:

```powershell
.\run_quality_checks.ps1
```

Script chạy:

1. Backend lint bằng Ruff.
2. Backend regression tests bằng pytest.
3. Frontend TypeScript check.
4. Frontend tests bằng Vitest.

Có thể bỏ qua từng phần:

```powershell
.\run_quality_checks.ps1 -SkipBackend
.\run_quality_checks.ps1 -SkipFrontend
```

### Backend

Khuyến nghị:

```powershell
.\run_backend_tests.ps1
```

Hoặc chạy từ thư mục `backend/`:

```powershell
.\venv\Scripts\python.exe -m pytest
```

Lint Python từ root repo:

```powershell
.\backend\venv\Scripts\python.exe -m ruff check backend
```

### Frontend

Chạy từ thư mục `frontend/`:

```powershell
npm run typecheck
npm test
```

Hoặc dùng script gộp:

```powershell
npm run verify
```

Build production nếu cần:

```powershell
npm run build
```

---

## Ghi chú vận hành

- SQLite local mặc định được neo về database trong `backend/` nếu `DATABASE_URL` không override.
- Nếu đổi database file, restore backup hoặc đổi `DATABASE_URL`, nên restart backend.
- Workspace deletion hiện là xóa khỏi local management database; cần review riêng nếu muốn thao tác destructive ở upstream.
- Member deletion gọi upstream trước rồi mới xóa local row.
- Invite creation đã xử lý idempotent với trường hợp upstream trả duplicate `invite_id`.
- Team Refresh Token có cả manual và auto flow:
  - manual qua nút/API `refresh-token`
  - auto qua background token refresh cycle
  - cả hai đều cần tool/token provider tự động đăng nhập và lấy token mới đã được cấu hình sẵn
  - backend không tự thay thế browser-login tool; backend chỉ gọi tool đó, nhận token, verify rồi lưu kết quả
  - có lock để tránh chạy trùng
  - có verify token mới trước khi mark success
  - có follow-up sync sau khi refresh thành công
- Nếu Team Refresh Token đang chạy, request sau sẽ nhận trạng thái `in_progress` thay vì tạo task trùng.
- Update token thủ công chỉ nên dùng khi anh chắc token mới đúng workspace/org.
- Personal Plan Sync không sync mọi account mỗi vòng; nó chỉ sync account đến hạn theo `next_plan_sync_at`.
- Nút `Reload` trên Personal Accounts chỉ đọc lại DB, không gọi ChatGPT upstream.
- Nút `Check Now` sync một personal account.
- Nút `Sync Plans` batch sync nhiều personal accounts ngay lập tức.
- Background Personal Plan Sync có batch/delay để giảm rủi ro Cloudflare/rate-limit.
- Khi debug realtime/background sync, bắt đầu từ:

```text
docs/SYNC_RUNBOOK.md
```

---

## Giới hạn hiện tại

- SSE hiện phù hợp nhất cho single-instance deployment.
- SQLite tiện cho local/internal use; PostgreSQL sẽ phù hợp hơn nếu scale lớn hoặc nhiều operator cùng dùng.
- Project phụ thuộc vào ChatGPT internal/team APIs, nên nếu upstream đổi contract thì backend cần cập nhật.
- Personal entitlement endpoint là internal API, cần defensive parsing và có thể phải điều chỉnh nếu upstream thay đổi payload.
- Multi-instance realtime delivery cần shared event infrastructure như Redis/pub-sub.
- Tool nên được vận hành trong môi trường có kiểm soát tốt vì có lưu token/account metadata.

---

## Security notice

Repository này phù hợp nhất cho môi trường nội bộ và workflow vận hành có kiểm soát.

Trước khi dùng production hoặc public repository, nên review kỹ:

- authentication và admin token
- secret storage
- token encryption/rotation
- access control
- audit logging
- database backup/restore
- chính sách compliance nội bộ
- rủi ro phụ thuộc upstream/internal APIs

Không nên commit file `.env`, token thật, database thật hoặc export chứa dữ liệu người dùng lên repository public.

---

## License

Thêm license mong muốn trước khi public repository.
