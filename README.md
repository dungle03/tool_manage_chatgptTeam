# ChatGPT Workspace Manager

Dashboard full-stack để quản lý nhiều **workspace ChatGPT Team** trong một nơi.

Dự án kết hợp **frontend Next.js** và **backend FastAPI** để import workspace, xem danh sách thành viên và invite, thực hiện các thao tác quản trị, đồng thời giữ dashboard luôn mới thông qua **background sync + SSE realtime updates**.

---

## Tổng quan

Repository này được xây dựng cho người vận hành nhiều workspace ChatGPT Team và cần một giao diện tập trung để:

- import và theo dõi nhiều workspace
- xem nhanh trạng thái thành viên và invite
- kick member và quản lý pending invite
- trigger manual sync khi cần
- nhận cập nhật gần realtime mà không cần reload trang

Ở thời điểm hiện tại, codebase đã ở trạng thái tốt cho **demo, sử dụng nội bộ và triển khai single-instance quy mô nhỏ**.

---

## Tính năng chính

### Quản lý workspace
- Import workspace bằng `access_token` hoặc `session_token`
- Hiển thị toàn bộ workspace trong một dashboard thống nhất
- Hiển thị số ghế đã dùng, tình trạng sync, ngày hết hạn và trạng thái hot-sync
- Xóa workspace khỏi danh sách quản lý cục bộ
- Trigger manual sync cho từng workspace

### Quản lý thành viên
- Xem danh sách member theo từng workspace
- Hiển thị ngày tham gia theo định dạng `dd/mm/yyyy`
- Kick member với luồng xác nhận rõ ràng
- Tô đỏ trực tiếp các member vượt quá giới hạn ghế
- Rule hiện tại: **mỗi team mặc định có 7 ghế; từ member active thứ 8 trở đi mới bị tô đỏ**

### Quản lý invite
- Mời member mới bằng email
- Gửi lại invite đang chờ
- Hủy invite đang chờ
- Theo dõi số invite pending theo từng workspace

### Realtime Sync V2
- Background worker của FastAPI khởi động cùng app lifespan
- Scheduler thông minh theo hot queue + follow-up sync windows
- Các action thủ công tự động trigger follow-up sync
- SSE stream đẩy cập nhật workspace lên dashboard
- Frontend có cơ chế dedupe event/toast để giảm nhiễu UI

### UI/UX
- Dashboard dark mode hiện đại
- Workspace card có thể expand/collapse với chevron animation
- Badge trạng thái cho sync state và hot workspace
- Layout gọn cho nhu cầu vận hành nhiều workspace cùng lúc

---

## Kiến trúc hệ thống

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

### Cấu trúc repository

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
│  ├─ PROJECT_REVIEW_20260312.md
│  └─ SYNC_RUNBOOK.md
├─ run_backend_tests.ps1
└─ README.md
```

---

## Tech stack

| Tầng | Công nghệ |
|------|-----------|
| Frontend | Next.js 14, React 18, TypeScript |
| Styling | Vanilla CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite |
| Realtime | Server-Sent Events (SSE) |
| Test backend | pytest |
| Test frontend | Vitest, Testing Library |

---

## Trạng thái hiện tại của dự án

### Những phần đang hoạt động tốt
- Import workspace và hiển thị dashboard
- Lấy và hiển thị danh sách member
- Luồng invite: create, resend, cancel
- Luồng kick member
- Background sync gắn với FastAPI lifespan
- Dashboard cập nhật lại qua SSE
- Workspace card đã được polish rõ hơn cho vận hành
- Bộ test frontend đã ổn định trên Windows
- Vấn đề chạy backend test đã được xác định nguyên nhân và document rõ

### Lưu ý quan trọng về backend test
Backend test có thể trông như bị “treo” nếu chạy từ **thư mục gốc của repository** bằng lệnh:

```powershell
python -m pytest backend/tests
```

Cách chạy đúng và ổn định là:

```powershell
# Chạy từ root repo
./run_backend_tests.ps1

# Hoặc chạy trực tiếp bên trong backend/
python -m pytest tests -vv
```

Dự án hiện đã có `run_backend_tests.ps1` để chuẩn hóa việc chạy backend test trong đúng working directory.

Nếu đang sửa luồng realtime/SSE, nên đọc thêm `docs/SYNC_RUNBOOK.md` để biết file cần kiểm tra và cách verify theo nhánh frontend/backend.

---

## Hướng dẫn khởi động nhanh

## 1. Cài đặt backend

Tạo virtual environment và cài dependencies:

```powershell
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Tạo file `backend/.env` từ `backend/.env.example` nếu cần.

Chạy backend **từ thư mục `backend/`**:

```powershell
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 2. Cài đặt frontend

```powershell
cd frontend
npm install
npm run dev
```

Mở trình duyệt tại [http://localhost:3000](http://localhost:3000).

---

## Biến môi trường

### Backend (`backend/.env`)

| Biến | Mặc định | Mục đích |
|------|----------|----------|
| `DATABASE_URL` | `sqlite:///./workspace_manager.db` | Chuỗi kết nối database backend |
| `SYNC_LOOP_INTERVAL_SECONDS` | `5` | Chu kỳ vòng lặp nền chính |
| `SYNC_STALE_MINUTES` | `5` | Ngưỡng xác định workspace stale |
| `SYNC_PENDING_INVITE_SECONDS` | `15` | Tăng tần suất kiểm tra khi có invite pending |
| `SYNC_BASELINE_MINUTES` | `5` | Chu kỳ refresh nền cơ bản |
| `SYNC_HOT_WINDOW_SECONDS` | `180` | Thời gian workspace được giữ ở trạng thái hot |
| `SYNC_FOLLOWUP_STEPS` | `5,15,30,60` | Các mốc follow-up sync sau action quan trọng |
| `SYNC_ERROR_RETRY_STEPS` | `10,30,60` | Các mốc retry sau khi sync lỗi |
| `SYNC_MAX_PARALLEL_WORKSPACES` | `2` | Số workspace sync song song tối đa |
| `ADMIN_TOKEN` | chưa đặt | Bảo vệ các admin endpoint của backend |
| `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC` | chưa đặt | Tắt background sync khi test hoặc chạy cô lập |

### Frontend (`frontend/.env.local`)

| Biến | Mục đích |
|------|----------|
| `NEXT_PUBLIC_ADMIN_TOKEN` | Token frontend gửi sang backend |

### Lệnh verify nhanh cho realtime/sync

```powershell
# Frontend realtime helper
cd frontend
npm test -- workspace-events.test.ts

# Backend sync/realtime regression
cd ..
pytest backend/tests/test_realtime_sync.py -q
```

---

## API chính

| Method | Endpoint | Mô tả |
|--------|----------|------|
| `GET` | `/api/workspaces` | Lấy danh sách workspace đang quản lý |
| `POST` | `/api/teams/import` | Import team/workspace từ token |
| `GET` | `/api/workspaces/{id}/members` | Lấy danh sách member của workspace |
| `GET` | `/api/workspaces/{id}/sync` | Trigger sync ngay lập tức |
| `DELETE` | `/api/workspaces/{id}` | Xóa workspace khỏi danh sách quản lý cục bộ |
| `POST` | `/api/invite` | Tạo invite mới |
| `GET` | `/api/invites?org_id=...` | Lấy danh sách invite đang chờ |
| `POST` | `/api/resend-invite` | Gửi lại invite |
| `DELETE` | `/api/cancel-invite` | Hủy invite |
| `DELETE` | `/api/member` | Kick member khỏi workspace |
| `GET` | `/api/events/workspaces` | Mở SSE stream cho event workspace |

---

## Chạy test

### Frontend
Trên Windows, nên chạy từ path thật của project để Vitest ổn định nhất:

```powershell
cd frontend
npm test
```

Nếu cần kiểm tra production build:

```powershell
npm run build
```

### Backend
Khuyến nghị:

```powershell
./run_backend_tests.ps1
```

Nếu muốn truyền thêm tham số pytest:

```powershell
./run_backend_tests.ps1 -PytestArgs @('tests', '-vv', '-x')
```

Cách khác (chạy trực tiếp trong `backend/`):

```powershell
python -m pytest tests -vv
```

> Không nên dùng `python -m pytest backend/tests` từ thư mục gốc repo, vì cách này có thể chạy sai context và tạo cảm giác test bị treo.

---

## Tóm tắt review (2026-03-12)

Bản review mới nhất nằm tại:

- [docs/PROJECT_REVIEW_20260312.md](file:///D:/laptrinh/laptrinh/code/LinhTinh/tool_manage_chatgptTeam/docs/PROJECT_REVIEW_20260312.md)
- `docs/SYNC_RUNBOOK.md` cho hướng dẫn sync/debug vận hành nhanh

Kết luận ở mức cao:
- Product đã đủ tính năng cho phạm vi nội bộ hiện tại
- Hành vi realtime và UX dashboard đang ở trạng thái tốt
- Quy trình test đã được document rõ và ổn định hơn
- Giới hạn lớn nhất khi scale vẫn là mô hình SSE/event dạng in-memory cho multi-instance

---

## Giới hạn hiện tại

- SSE/event delivery hiện phù hợp nhất cho **single-instance deployment**
- SQLite tiện cho local/dev và triển khai nội bộ nhỏ, nhưng nếu scale lớn nên chuyển PostgreSQL
- Dự án phụ thuộc vào ChatGPT internal/team APIs, nên nếu upstream thay đổi contract thì backend có thể cần cập nhật
- Các lệnh test frontend đáng tin cậy hơn khi chạy từ path thật trên Windows thay vì path symlink

---

## Bước tiếp theo được khuyến nghị

- Thêm Redis/pub-sub nếu cần realtime multi-instance
- Bổ sung test end-to-end cho SSE và sync scheduling
- Viết thêm tài liệu deploy cho môi trường staging/production
- Dùng `docs/SYNC_RUNBOOK.md` làm điểm bắt đầu khi debug sync/realtime
- Cân nhắc chuyển sang PostgreSQL nếu cần dùng chung ở quy mô lớn hơn

---

## Ghi chú sử dụng

Repository này hiện đang được chuẩn bị như một công cụ vận hành nội bộ. Trước khi rollout production, nên review thêm các yêu cầu về bảo mật, phân quyền và compliance của tổ chức.
