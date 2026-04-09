# ChatGPT Workspace Manager

[🇻🇳 Tiếng Việt](./README.md) | [🇺🇸 English](./README.en.md)

Dashboard full-stack để quản lý nhiều **workspace ChatGPT Team** trong một nơi.

Dự án kết hợp **frontend Next.js** và **backend FastAPI** để import workspace, xem danh sách thành viên và invite, thực hiện các thao tác quản trị, đồng thời giữ dashboard luôn mới thông qua **background sync** và **SSE realtime updates**.

---

## Tổng quan

Việc quản lý nhiều workspace ChatGPT Team theo cách thủ công thường chậm, lặp lại và khó kiểm soát. Project này gom toàn bộ quy trình vận hành về một dashboard duy nhất để anh có thể:

- import và theo dõi nhiều workspace
- xem nhanh thành viên và invite đang chờ
- kick member và xử lý pending invite
- trigger manual sync khi cần
- nhận cập nhật gần realtime mà không cần reload trang
- theo dõi unauthorized member và luồng auto-kick
- theo dõi trạng thái refresh token và sức khỏe sync của workspace

Codebase hiện phù hợp nhất cho:

- công cụ nội bộ
- triển khai single-instance
- dashboard vận hành
- môi trường local/dev hoặc controlled environment

---

## Tính năng chính

### Quản lý workspace

- Import workspace bằng `access_token`
- Hiển thị toàn bộ workspace trong một dashboard thống nhất
- Theo dõi tên team, organization ID, số ghế đã dùng, trạng thái sync và ngày hết hạn
- Xóa workspace khỏi database quản lý cục bộ
- Trigger manual sync cho từng workspace
- Scheduler nền tự xử lý stale workspace và hot workspace

### Quản lý thành viên

- Xem danh sách member theo từng workspace
- Hiển thị tên, email, role và thời gian tham gia
- Kick member với luồng xác nhận rõ ràng
- Persist member state trong local database
- Highlight các trường hợp vượt seat limit

### Quản lý invite

- Tạo invite mới bằng email
- Gửi lại invite đang chờ
- Hủy invite đang chờ
- Theo dõi số invite pending theo từng workspace
- Xử lý an toàn trường hợp upstream trả về `invite_id` bị trùng

### Kiểm soát unauthorized member

- Phát hiện member tồn tại ở upstream nhưng không có trong local whitelist
- Hỗ trợ cả `auto_kick` và manual review
- Lưu trạng thái unauthorized findings theo lịch sử xử lý
- Tự động resolve finding khi member đã được xóa hoặc trạng thái đã đồng bộ lại

### Token refresh và realtime sync

- Background worker khởi động cùng FastAPI lifespan
- Scheduler thông minh với hot-window và follow-up sync
- Token refresh lifecycle được persist trong database
- SSE đẩy cập nhật workspace lên dashboard gần realtime
- Frontend có cơ chế dedupe event/toast để giảm nhiễu UI

### Công cụ export dữ liệu

- Có sẵn tool Python để export team/member từ local database:
  - `backend/export_workspace_members.py`

---

## Kiến trúc hệ thống

```text
Frontend (Next.js / React / TypeScript)
        |
        v
Backend API (FastAPI)
        |
        +--> SQLAlchemy ORM
        +--> SQLite database (mặc định)
        +--> Background sync scheduler
        +--> SSE event stream
        +--> ChatGPT internal/team APIs
```

### Luồng runtime chính

1. Frontend gọi backend API cho các action workspace, member và invite.
2. Backend persist trạng thái vận hành vào local database.
3. Background scheduler liên tục kiểm tra workspace nào cần sync hoặc refresh token.
4. Backend phát SSE event khi trạng thái workspace thay đổi.
5. Frontend lắng nghe SSE để cập nhật card, banner và toast.

---

## Cấu trúc repository

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
│  ├─ export_workspace_members.py
│  ├─ seed.py
│  ├─ pytest.ini
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/
│  ├─ src/components/
│  ├─ src/lib/
│  ├─ src/types/
│  └─ package.json
├─ docs/
│  ├─ PROJECT_REVIEW_20260312.md
│  ├─ PROJECT_REVIEW_20260407.md
│  └─ SYNC_RUNBOOK.md
├─ run_backend_tests.ps1
├─ start_dashboard.ps1
├─ README.md
└─ README.en.md
```

---

## Tech stack

| Tầng          | Công nghệ                        |
| ------------- | -------------------------------- |
| Frontend      | Next.js 14, React 18, TypeScript |
| Styling       | Vanilla CSS                      |
| Backend       | FastAPI, SQLAlchemy, Pydantic    |
| Database      | SQLite mặc định                  |
| Realtime      | Server-Sent Events (SSE)         |
| Test backend  | pytest                           |
| Test frontend | Vitest, Testing Library          |

### Yêu cầu runtime

- **Python**: khuyến nghị 3.11+
- **Node.js**: `>= 22.12.0`

---

## Quick Start

### 1. Cài backend

```powershell
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Tạo `backend/.env` từ `backend/.env.example` nếu cần.

Chạy backend từ thư mục `backend/`:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### 2. Cài frontend

Chạy frontend từ thư mục `frontend/`:

```powershell
npm install
npm run dev
```

Mở trình duyệt tại: [http://localhost:3000](http://localhost:3000)

---

## Biến môi trường

### Backend (`backend/.env`)

| Biến                                        | Mặc định                           | Mục đích                                      |
| ------------------------------------------- | ---------------------------------- | --------------------------------------------- |
| `DATABASE_URL`                              | `sqlite:///./workspace_manager.db` | Chuỗi kết nối database backend                |
| `SYNC_LOOP_INTERVAL_SECONDS`                | `5`                                | Chu kỳ vòng lặp nền chính                     |
| `SYNC_STALE_MINUTES`                        | `5`                                | Ngưỡng xác định workspace stale               |
| `SYNC_PENDING_INVITE_SECONDS`               | `15`                               | Tăng tần suất kiểm tra khi có invite pending  |
| `SYNC_BASELINE_MINUTES`                     | `5`                                | Chu kỳ refresh nền cơ bản                     |
| `SYNC_HOT_WINDOW_SECONDS`                   | `180`                              | Thời gian workspace được giữ ở trạng thái hot |
| `SYNC_FOLLOWUP_STEPS`                       | `5,15,30,60`                       | Các mốc follow-up sync sau action quan trọng  |
| `SYNC_ERROR_RETRY_STEPS`                    | `10,30,60`                         | Các mốc retry sau khi sync lỗi                |
| `SYNC_MAX_PARALLEL_WORKSPACES`              | `2`                                | Số workspace sync song song tối đa            |
| `ADMIN_TOKEN`                               | chưa đặt                           | Bảo vệ các admin endpoint                     |
| `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC` | chưa đặt                           | Tắt background sync khi test hoặc chạy cô lập |

### Frontend (`frontend/.env.local`)

| Biến                      | Mục đích                        |
| ------------------------- | ------------------------------- |
| `NEXT_PUBLIC_ADMIN_TOKEN` | Token frontend gửi sang backend |

---

## API chính

| Method   | Endpoint                             | Mô tả                                |
| -------- | ------------------------------------ | ------------------------------------ |
| `GET`    | `/api/workspaces`                    | Lấy danh sách workspace đang quản lý |
| `POST`   | `/api/teams/import`                  | Import workspace/team từ token       |
| `POST`   | `/api/workspaces/{id}/sync`          | Trigger sync ngay lập tức            |
| `POST`   | `/api/workspaces/{id}/refresh-token` | Trigger refresh token                |
| `DELETE` | `/api/workspaces/{id}`               | Xóa workspace khỏi local database    |
| `GET`    | `/api/workspaces/{id}/members`       | Lấy danh sách member của workspace   |
| `DELETE` | `/api/member`                        | Kick member khỏi workspace           |
| `POST`   | `/api/invite`                        | Tạo invite mới                       |
| `POST`   | `/api/resend-invite`                 | Gửi lại invite đang chờ              |
| `DELETE` | `/api/cancel-invite`                 | Hủy invite đang chờ                  |
| `GET`    | `/api/invites?org_id=...`            | Lấy danh sách invite của workspace   |
| `GET`    | `/api/events/workspaces`             | Mở SSE stream                        |

---

## Tóm tắt database model

### `workspaces`

Lưu trạng thái vận hành của từng workspace đã import:

- tên team
- org/account ID
- access token
- ngày hết hạn
- metadata sync và scheduling
- trạng thái token refresh

### `members`

Lưu snapshot member theo từng workspace:

- remote member ID
- tên
- email
- role
- thời gian tham gia

### `invites`

Lưu trạng thái invite:

- email
- invite ID
- pending status
- cờ đánh dấu invite có phải do tool tạo hay không

### `unauthorized_findings`

Lưu lịch sử phát hiện và xử lý unauthorized member:

- remote ID
- email
- role
- trạng thái finding hiện tại
- action reason
- thời điểm first seen, last seen, resolved

---

## Export dữ liệu team và member

Có sẵn tool export độc lập:

- `backend/export_workspace_members.py`

Ví dụ chạy:

```powershell
python export_workspace_members.py --format csv --output exports/team_members_export.csv --include-empty-teams
```

Các cột export:

- `team_name`
- `team_id`
- `team_expires_at`
- `member_name`
- `member_email`
- `member_role`
- `member_joined_at`

---

## Chạy test

### Frontend

```powershell
npm test
```

Nếu cần build production:

```powershell
npm run build
```

### Backend

Khuyến nghị:

```powershell
./run_backend_tests.ps1
```

Cách khác:

```powershell
python -m pytest tests -vv
```

> Không nên chạy `python -m pytest backend/tests` từ thư mục gốc repo vì dễ chạy sai context và tạo cảm giác test bị treo.

---

## Ghi chú vận hành

- Xóa member sẽ gọi upstream trước, sau đó mới xóa row trong local database.
- Xóa workspace sẽ xóa workspace và dữ liệu liên quan trong local database.
- Luồng xóa workspace hiện tại là xóa khỏi hệ thống quản lý cục bộ; nếu cần xem hành vi xóa upstream thì nên review riêng.
- Auto-kick unauthorized member phụ thuộc vào remote member identifier từ payload upstream.
- Tạo invite hiện đã idempotent với trường hợp upstream trả về `invite_id` bị trùng.

Khi cần debug realtime/background sync, nên bắt đầu với:

- `docs/SYNC_RUNBOOK.md`

---

## Giới hạn hiện tại

- SSE hiện phù hợp nhất cho **single-instance deployment**.
- SQLite tiện cho local/internal use, nhưng PostgreSQL sẽ phù hợp hơn nếu scale lớn.
- Project phụ thuộc vào ChatGPT internal/team APIs, nên nếu upstream đổi contract thì backend có thể phải cập nhật.
- Nếu cần realtime multi-instance thì nên có shared event infrastructure như Redis/pub-sub.

---

## Security notice

Repository này phù hợp nhất cho môi trường kiểm soát tốt và workflow vận hành nội bộ.

Trước khi dùng ở production, nên review thêm:

- cách quản lý authentication và admin token
- chiến lược lưu secret
- access control
- yêu cầu compliance nội bộ
- rủi ro khi phụ thuộc upstream API

---

## License

Anh có thể thêm license mong muốn vào đây trước khi public repository.
