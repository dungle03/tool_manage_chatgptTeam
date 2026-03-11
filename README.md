# ChatGPT Workspace Manager

Dashboard hợp nhất để quản lý nhiều **workspace ChatGPT Team** trong một nơi.

Bạn có thể import team, xem thành viên, quản lý invite, xóa member, sync dữ liệu thủ công và nhận cập nhật gần realtime qua **SSE + Realtime Sync V2**.

---

## Tính năng chính

### Quản lý workspace
- Import team bằng `access_token` hoặc `session_token`
- Xem tất cả workspace trên một dashboard duy nhất
- Xóa workspace khỏi danh sách quản lý cục bộ
- Hiển thị số ghế đã dùng, trạng thái sync và ngày hết hạn team

### Quản lý thành viên
- Xem danh sách thành viên theo từng workspace
- Hiển thị ngày tham gia member theo định dạng `dd/mm/yyyy`
- Xóa member với luồng xác nhận rõ ràng
- Hiển thị role và đánh dấu member vượt giới hạn ghế trên UI

### Quản lý invite
- Mời member mới bằng email
- Gửi lại invite đang chờ
- Hủy invite đang chờ
- Theo dõi số invite pending theo từng workspace

### Realtime Sync V2
- Background sync worker khởi động cùng FastAPI lifespan
- Scheduler thông minh dùng cơ chế hot queue + follow-up sync
- Ưu tiên sync cho workspace đang “hot” hoặc có pending invites
- Dùng Server-Sent Events (SSE) để cập nhật dashboard
- Frontend xử lý các event:
  - `sync_started`
  - `workspace_updated`
  - `sync_failed`
  - `workspace_scheduled`
  - `heartbeat`

### Điểm nổi bật giao diện
- Dashboard dark mode theo phong cách hiện đại
- Icon SVG chevron có animation xoay cho phần expand/collapse workspace
- Hiển thị ngày hết hạn team ngay dưới tên workspace
- Hiển thị trạng thái sync, hot state và sync reason ngay trên workspace card

---

## Kiến trúc hệ thống

```text
Frontend (Next.js) -> Backend API (FastAPI) -> ChatGPT Internal API
                         |
                         +-> SQLite / PostgreSQL
                         |
                         +-> Background Sync Worker
                         |
                         +-> SSE Event Stream
```

### Cấu trúc thư mục chính

```text
tool_manage_chatgptTeam/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ db.py
│  │  ├─ models.py
│  │  ├─ routers/
│  │  ├─ schemas.py
│  │  └─ services/
│  ├─ tests/
│  └─ requirements.txt
├─ frontend/
│  ├─ src/app/
│  ├─ src/components/
│  ├─ src/lib/
│  └─ src/types/
├─ docs/
│  ├─ DESIGN.md
│  └─ PROJECT_REVIEW_20260312.md
└─ README.md
```

---

## Công nghệ sử dụng

| Tầng | Công nghệ |
|------|-----------|
| Frontend | Next.js 14, React 18, TypeScript |
| Styling | Vanilla CSS |
| Backend | FastAPI, SQLAlchemy, Pydantic |
| Database | SQLite (dev), sẵn sàng cho PostgreSQL |
| Realtime | Server-Sent Events (SSE) |
| Test backend | pytest |
| Test frontend | Vitest, Testing Library |

---

## Hướng dẫn chạy nhanh

## 1) Backend

```bash
python -m venv backend/venv
backend\venv\Scripts\activate
pip install -r backend/requirements.txt
```

Tạo file `backend/.env` từ `backend/.env.example` rồi chỉnh lại giá trị nếu cần.

Chạy API:

```bash
uvicorn app.main:app --reload --port 8000
```

> Hãy chạy lệnh này trong thư mục `backend/`.

## 2) Frontend

```bash
cd frontend
npm install
npm run dev
```

Mở trình duyệt tại: [http://localhost:3000](http://localhost:3000)

---

## Biến môi trường

### Backend (`backend/.env`)

| Biến | Mặc định | Mục đích |
|------|----------|----------|
| `DATABASE_URL` | `sqlite:///./workspace_manager.db` | Chuỗi kết nối database |
| `SYNC_LOOP_INTERVAL_SECONDS` | `5` | Chu kỳ chạy vòng lặp nền |
| `SYNC_STALE_MINUTES` | `5` | Ngưỡng stale cũ |
| `SYNC_PENDING_INVITE_SECONDS` | `15` | Tăng tần suất check khi có invite pending |
| `SYNC_BASELINE_MINUTES` | `5` | Chu kỳ refresh nền cơ bản |
| `SYNC_HOT_WINDOW_SECONDS` | `180` | Thời gian workspace được giữ ở trạng thái hot |
| `SYNC_FOLLOWUP_STEPS` | `5,15,30,60` | Các mốc follow-up sync sau action quan trọng |
| `SYNC_ERROR_RETRY_STEPS` | `10,30,60` | Các mốc retry sau khi sync lỗi |
| `SYNC_MAX_PARALLEL_WORKSPACES` | `2` | Số workspace sync song song tối đa |
| `ADMIN_TOKEN` | _chưa đặt_ | Bảo vệ API backend |

### Frontend (`frontend/.env.local`)

| Biến | Mục đích |
|------|----------|
| `NEXT_PUBLIC_ADMIN_TOKEN` | Gửi token xác thực từ dashboard lên backend |

---

## Tổng quan API

| Method | Endpoint | Mô tả |
|--------|----------|------|
| `GET` | `/api/workspaces` | Lấy danh sách workspace đang quản lý |
| `POST` | `/api/teams/import` | Import một hoặc nhiều team từ token |
| `GET` | `/api/workspaces/{id}/members` | Lấy danh sách member của workspace |
| `GET` | `/api/workspaces/{id}/sync` | Kích hoạt manual sync |
| `DELETE` | `/api/workspaces/{id}` | Xóa workspace khỏi hệ thống quản lý |
| `POST` | `/api/invite` | Mời member mới |
| `GET` | `/api/invites?org_id=...` | Lấy danh sách invite đang chờ |
| `POST` | `/api/resend-invite` | Gửi lại invite |
| `DELETE` | `/api/cancel-invite` | Hủy invite |
| `DELETE` | `/api/member` | Xóa member khỏi workspace |
| `GET` | `/api/events/workspaces` | Mở SSE stream cho event workspace |

---

## Chạy test

### Frontend

```bash
cd frontend
npm test
npm run build
```

### Backend

```bash
cd backend
python -m pytest backend/tests
```

> Lưu ý: gần đây đã có trường hợp lệnh pytest backend chạy lâu bất thường. Nếu hiện tượng này lặp lại, nên kiểm tra test đang treo hoặc vòng đời background worker trước khi deploy production.

---

## Xác thực

Khi `ADMIN_TOKEN` được cấu hình ở backend, các endpoint được bảo vệ sẽ yêu cầu header:

```http
Authorization: Bearer <your-token>
```

Với SSE trên trình duyệt, frontend có thể truyền `admin_token` qua query parameter khi cần.

---

## Trạng thái hiện tại

Dự án hiện đã có:
- dashboard quản lý workspace hoạt động tốt
- các thao tác member và invite
- Realtime Sync V2
- dashboard cập nhật bằng SSE
- UI workspace card đã được polish thêm

Hiện trạng phù hợp để dùng cho **demo, staging và production quy mô nhỏ/nội bộ**, với vấn đề lớn nhất còn cần điều tra là thời gian chạy test backend quá lâu trong một số trường hợp.

---

## Giới hạn hiện tại

- SSE broker hiện đang là in-memory nên phù hợp nhất cho single-instance deployment.
- Thời gian chạy full backend pytest vẫn cần điều tra thêm.
- Nếu muốn scale nhiều instance, nên nâng cấp hạ tầng realtime sang Redis pub/sub hoặc message broker tương đương.

---

## Bước tiếp theo được khuyến nghị

1. Điều tra nguyên nhân backend test bị treo lâu
2. Chạy lại test backend và frontend một lần sạch
3. Deploy lên staging
4. Nếu cần scale nhiều instance, nâng cấp tầng realtime broker
