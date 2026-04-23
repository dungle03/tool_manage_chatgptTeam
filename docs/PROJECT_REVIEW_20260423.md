# 📊 BÁO CÁO DỰ ÁN: ChatGPT Workspace Manager

**Ngày review:** 2026-04-23  
**Mục tiêu:** Tổng hợp đầy đủ chức năng, cách hoạt động và tình trạng hiện tại của project sau khi rollback về commit gần nhất.

---

## 🎯 App này dùng để làm gì?

Đây là một **dashboard full-stack** để quản lý nhiều **workspace ChatGPT Team** tại một nơi.

Thay vì phải vào từng workspace thủ công để xem thành viên, lời mời, sync hay xử lý thành viên lạ, project này gom toàn bộ về một dashboard vận hành duy nhất.

Nói ngắn gọn, app giúp anh:

- import nhiều workspace bằng `access_token`
- theo dõi tình trạng từng workspace
- xem member và pending invite
- kick member khỏi workspace
- tạo / gửi lại / hủy invite
- phát hiện thành viên lạ (unauthorized member)
- sync thủ công hoặc để background worker tự sync
- nhận cập nhật gần realtime qua SSE
- theo dõi vòng đời refresh token

---

## 📦 Tình trạng hiện tại của project

Hiện tại project đã được **rollback về commit gần nhất** và working tree đang sạch.

Điều đó có nghĩa là:

- code hiện tại là trạng thái đã commit gần nhất
- các thay đổi debug/fix thử nghiệm gần đây không còn trong repo
- đây là trạng thái phù hợp để review, bàn giao hoặc lên kế hoạch bước tiếp theo

### Đánh giá nhanh

| Hạng mục         | Trạng thái     | Nhận xét                                                        |
| ---------------- | -------------- | --------------------------------------------------------------- |
| Repo             | ✅ Ổn định     | Đã rollback về commit gần nhất                                  |
| Kiến trúc        | ✅ Khá rõ      | Frontend + FastAPI + SQLite + background sync                   |
| Chức năng lõi    | ✅ Đầy đủ      | import, sync, member, invite, unauthorized, token refresh       |
| Tài liệu         | ✅ Có sẵn      | README, DESIGN, SYNC_RUNBOOK, review cũ                         |
| Test             | 🟡 Có nền tảng | Có test backend/frontend, nhưng cần re-run khi làm thay đổi lớn |
| Production scale | 🟡 Hạn chế     | Hiện tối ưu cho single-instance/internal tool                   |

---

## 🧱 Cấu trúc chính của project

```text
tool_manage_chatgptTeam/
├─ backend/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ db.py
│  │  ├─ models.py
│  │  ├─ schemas.py
│  │  ├─ auth.py
│  │  ├─ routers/
│  │  └─ services/
│  ├─ tests/
│  ├─ requirements.txt
│  ├─ seed.py
│  └─ export_workspace_members.py
├─ frontend/
│  ├─ src/app/
│  ├─ src/components/
│  ├─ src/lib/
│  ├─ src/types/
│  └─ package.json
├─ docs/
│  ├─ DESIGN.md
│  ├─ SYNC_RUNBOOK.md
│  ├─ PROJECT_REVIEW_20260407.md
│  └─ ...
├─ README.md
├─ README.en.md
├─ run_backend_tests.ps1
├─ start_dashboard.ps1
└─ workspace_manager.db
```

---

## 🛠️ Công nghệ sử dụng

| Thành phần    | Công nghệ                        |
| ------------- | -------------------------------- |
| Frontend      | Next.js 14, React 18, TypeScript |
| Styling       | Vanilla CSS                      |
| Backend       | FastAPI                          |
| ORM           | SQLAlchemy                       |
| Validation    | Pydantic                         |
| Database      | SQLite                           |
| Realtime      | SSE (Server-Sent Events)         |
| Backend test  | pytest                           |
| Frontend test | Vitest + Testing Library         |

### Runtime yêu cầu

- **Node.js:** `>= 22.12.0`
- **Python:** README khuyến nghị `3.11+`

---

## 🚀 Cách chạy project

### Backend

Từ thư mục `backend/`:

```powershell
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

### Frontend

Từ thư mục `frontend/`:

```powershell
npm install
npm run dev
```

Mở:

- Frontend: `http://localhost:3000`
- Backend API: `http://127.0.0.1:8000`

---

## 🔐 Biến môi trường chính

### Backend

File: `backend/.env`

Biến quan trọng:

- `DATABASE_URL`
- `ADMIN_TOKEN`
- `SYNC_LOOP_INTERVAL_SECONDS`
- `SYNC_STALE_MINUTES`
- `SYNC_PENDING_INVITE_SECONDS`
- `SYNC_BASELINE_MINUTES`
- `SYNC_HOT_WINDOW_SECONDS`
- `SYNC_FOLLOWUP_STEPS`
- `SYNC_ERROR_RETRY_STEPS`
- `SYNC_MAX_PARALLEL_WORKSPACES`
- `WORKSPACE_MANAGER_DISABLE_BACKGROUND_SYNC`

### Frontend

File: `frontend/.env.local`

- `NEXT_PUBLIC_ADMIN_TOKEN`

---

## 🧠 Kiến trúc hoạt động tổng quát

```text
Frontend dashboard (Next.js)
        |
        v
Backend API (FastAPI)
        |
        +--> Router layer
        +--> Service layer
        +--> SQLAlchemy ORM
        +--> SQLite database
        +--> Background sync worker
        +--> SSE broker
        +--> ChatGPT team/internal APIs
```

### Ý nghĩa từng lớp

| Khu vực                     | Vai trò                                                   |
| --------------------------- | --------------------------------------------------------- |
| `frontend/src/app/page.tsx` | Orchestrator UI chính của dashboard                       |
| `frontend/src/components/`  | Các khối giao diện như card, bảng member, invite panel    |
| `frontend/src/lib/api.ts`   | API client gọi backend                                    |
| `backend/app/routers/`      | Các endpoint public cho dashboard                         |
| `backend/app/services/`     | Business logic: sync, token refresh, events, unauthorized |
| `backend/app/models.py`     | Mô hình dữ liệu SQLite                                    |
| `backend/app/main.py`       | Khởi tạo FastAPI, CORS, background worker                 |

---

## 🗂️ Database hiện đang lưu gì?

Từ `backend/app/models.py`, hệ thống có 4 bảng lõi:

### 1. `workspaces`

Lưu thông tin workspace đã import:

- `org_id`, `account_id`
- tên workspace
- `access_token`
- `member_count`, `member_limit`
- `expires_at`
- metadata sync như `last_sync`, `next_sync_at`, `hot_until`
- metadata refresh token như `last_token_refresh_at`, `last_token_refresh_error`
- policy `unauthorized_member_mode`

### 2. `members`

Lưu snapshot thành viên theo workspace:

- `remote_id`
- tên
- email
- role
- status
- thời điểm join/invite

### 3. `invites`

Lưu trạng thái invite:

- email
- `invite_id`
- status
- `created_by_tool`
- thời gian tạo

### 4. `unauthorized_findings`

Lưu thành viên bị xem là lạ / chưa được whitelist:

- `remote_id`
- email, tên, role
- trạng thái finding
- lý do detect / action
- `first_seen_at`, `last_seen_at`, `resolved_at`

---

## ✅ Các chức năng hiện có

## 1. Quản lý workspace

### Có gì?

- Import workspace bằng `access_token`
- Hiển thị danh sách workspace trong dashboard
- Xem trạng thái sync, số thành viên, số ghế, ngày hết hạn
- Đổi tên workspace
- Xóa workspace khỏi local database quản lý
- Trigger sync thủ công
- Trigger refresh token

### Hoạt động như thế nào?

1. Frontend gọi API import hoặc sync.
2. Backend lấy thông tin từ upstream ChatGPT team APIs.
3. Backend lưu dữ liệu vào bảng `workspaces`.
4. Background worker tiếp tục theo dõi workspace để sync định kỳ.
5. Frontend render danh sách workspace và nhận cập nhật qua SSE.

---

## 2. Quản lý thành viên

### Có gì?

- Xem danh sách member theo workspace
- Hiển thị tên, email, role, thời gian tham gia
- Kick member khỏi workspace
- Chặn thao tác nguy hiểm như xóa owner

### Flow hoạt động

1. Frontend mở chi tiết workspace.
2. Gọi `GET /api/workspaces/{id}/members`.
3. Backend trả member từ local DB.
4. Khi kick member, backend gọi upstream trước.
5. Nếu thành công mới xóa local record và update summary.
6. Sau đó follow-up sync để chốt trạng thái.

---

## 3. Quản lý invite

### Có gì?

- Tạo invite mới
- Gửi lại invite đang pending
- Hủy invite đang pending
- Xem danh sách pending invite
- Hiển thị pending invite count trên workspace

### Flow chung

1. User nhập email tại `InvitePanel`.
2. Frontend gọi endpoint invite tương ứng.
3. Backend resolve workspace + access token.
4. Backend gọi upstream API để tạo/resend/cancel invite.
5. Backend cập nhật bảng `invites`.
6. Backend trả về payload mutation để frontend cập nhật UI.
7. Sync nền/follow-up sync giúp dashboard cập nhật snapshot mới hơn.

> [!WARNING]
> Trạng thái hiện tại của project vẫn đang có vấn đề thực tế mà anh vừa gặp: pending invite có thể biến mất sau refresh/F5 trong một số case runtime. Vì repo đã rollback về commit gần nhất, lỗi này hiện chưa được xử lý dứt điểm trong trạng thái code hiện tại.

---

## 4. Kiểm soát unauthorized member

### Có gì?

- Phát hiện member tồn tại ở upstream nhưng không nằm trong local whitelist
- Hỗ trợ policy:
  - `off`
  - `warn_only`
  - `auto_kick`
- Lưu lịch sử finding
- Resolve finding khi trạng thái remote/local đồng bộ lại

### Flow hoạt động

1. Trong lúc sync member, backend so sánh remote snapshot với local whitelist.
2. Nếu phát hiện member lạ, tạo hoặc cập nhật `UnauthorizedFinding`.
3. Tùy policy của workspace, hệ thống có thể:
   - chỉ cảnh báo
   - hoặc tự kick member
4. Dashboard hiển thị finding để review thủ công.

---

## 5. Background sync

### Có gì?

- Worker nền chạy cùng FastAPI lifespan
- Scheduler chọn workspace cần sync
- Hỗ trợ baseline sync, hot window, retry, follow-up steps
- Tăng tần suất kiểm tra khi có pending invite hoặc khi vừa có action quan trọng

### Flow hoạt động

1. `backend/app/main.py` start background worker nếu env không tắt.
2. Worker quét workspace theo thời điểm `next_sync_at` và priority.
3. Gọi các service sync để đồng bộ member/invite/account info.
4. Cập nhật local DB.
5. Publish event để frontend update.

---

## 6. Token refresh lifecycle

### Có gì?

- Trigger refresh token cho workspace
- Persist kết quả refresh thành công/thất bại
- Lưu fail count và thông tin block/error
- Follow-up sync sau refresh thành công

### Ý nghĩa thực tế

Khi token cũ không còn dùng tốt, hệ thống có thể refresh và ghi nhận rõ tình trạng thay vì để dashboard im lặng lỗi mơ hồ.

---

## 7. Realtime update qua SSE

### Có gì?

- Frontend mở stream `GET /api/events/workspaces`
- Backend push event khi workspace đổi trạng thái
- Frontend cập nhật card, toast, banner theo event mới
- Có cơ chế dedupe event/toast để giảm nhiễu UI

### Ý nghĩa

Dashboard không cần F5 liên tục mà vẫn cập nhật được tương đối realtime.

---

## 8. Export dữ liệu team/member

Có sẵn script:

- `backend/export_workspace_members.py`

Dùng để export danh sách team/member từ local database, ví dụ ra CSV.

---

## 🌐 API chính hiện có

| Method   | Endpoint                             | Chức năng                   |
| -------- | ------------------------------------ | --------------------------- |
| `GET`    | `/api/workspaces`                    | Lấy danh sách workspace     |
| `POST`   | `/api/teams/import`                  | Import workspace từ token   |
| `POST`   | `/api/workspaces/{id}/sync`          | Sync workspace ngay         |
| `POST`   | `/api/workspaces/{id}/refresh-token` | Refresh token               |
| `DELETE` | `/api/workspaces/{id}`               | Xóa workspace khỏi local DB |
| `GET`    | `/api/workspaces/{id}/members`       | Lấy member                  |
| `DELETE` | `/api/member`                        | Kick member                 |
| `POST`   | `/api/invite`                        | Tạo invite                  |
| `POST`   | `/api/resend-invite`                 | Gửi lại invite              |
| `DELETE` | `/api/cancel-invite`                 | Hủy invite                  |
| `GET`    | `/api/invites?org_id=...`            | Lấy danh sách invite        |
| `GET`    | `/api/events/workspaces`             | Mở SSE stream               |

---

## 🖥️ Frontend hiện hoạt động ra sao?

Từ `frontend/src/app/page.tsx`, dashboard đang là một trang điều phối khá lớn.

### Nó đang làm những việc chính sau:

- load danh sách workspace
- lưu state chi tiết từng workspace (`members`, `invites`, `syncing`, ...)
- mở SSE stream và xử lý reconnect
- quản lý toast
- trigger refresh workspace list / workspace detail sau action
- render compact view và detail view
- gọi các mutation như invite, kick, sync, rename, token refresh

### Điểm mạnh

- UI đủ nhiều chức năng vận hành
- có refresh hint và event-driven update
- có dedupe toast/event

### Điểm cần lưu ý

- `page.tsx` vẫn còn khá dày, mang nhiều orchestration logic
- nếu phát triển thêm nhiều tính năng, nên tách dần ra custom hooks hoặc action modules để dễ maintain hơn

---

## 🧪 Tình trạng test hiện tại

Project có:

### Backend

- thư mục `backend/tests/`
- chạy bằng `pytest`
- có script `run_backend_tests.ps1`

### Frontend

- thư mục `frontend/src/__tests__/`
- dùng `Vitest` + `Testing Library`

### Đánh giá

- test foundation đã có
- có coverage cho nhiều flow chính
- phù hợp để làm regression khi sửa các flow nhạy cảm
- tuy nhiên, trước các bug runtime khó tái hiện như invite persistence, vẫn cần test thực tế thêm chứ không nên chỉ tin vào unit/regression test

---

## 📍 Các file quan trọng nên biết khi tiếp nhận

| File                                             | Vai trò                                |
| ------------------------------------------------ | -------------------------------------- |
| `README.md`                                      | Overview tổng thể, cách chạy, env, API |
| `docs/SYNC_RUNBOOK.md`                           | Runbook để debug sync/realtime         |
| `docs/DESIGN.md`                                 | Tài liệu thiết kế hệ thống             |
| `backend/app/main.py`                            | Khởi động FastAPI + background worker  |
| `backend/app/models.py`                          | Mô hình dữ liệu                        |
| `backend/app/routers/workspaces.py`              | API liên quan workspace                |
| `backend/app/routers/members.py`                 | API kick member                        |
| `backend/app/routers/invites.py`                 | API invite                             |
| `backend/app/services/workspace_sync.py`         | Điều phối sync                         |
| `backend/app/services/token_refresher.py`        | Flow refresh token                     |
| `backend/app/services/workspace_unauthorized.py` | Logic unauthorized member              |
| `frontend/src/app/page.tsx`                      | Dashboard orchestration chính          |
| `frontend/src/lib/api.ts`                        | API client phía frontend               |

---

## ✅ Điểm mạnh hiện tại của project

1. **Chức năng khá đầy đủ** cho một dashboard vận hành nội bộ.
2. **Kiến trúc rõ ràng hơn** so với dạng dồn hết vào một file lớn.
3. **Có background sync + SSE**, giúp trải nghiệm vận hành tốt hơn tool CRUD đơn thuần.
4. **Có unauthorized member handling**, đây là điểm nghiệp vụ khá đặc thù và giá trị.
5. **Có token refresh lifecycle**, tăng tính bền khi vận hành workspace dài hạn.
6. **Tài liệu repo khá tốt**, giúp tiếp nhận nhanh.

---

## ⚠️ Hạn chế / rủi ro hiện tại

| Vấn đề                                             | Mức độ        | Ghi chú                                                           |
| -------------------------------------------------- | ------------- | ----------------------------------------------------------------- |
| Invite persistence sau F5 chưa ổn định             | 🔴 Cao        | Là lỗi thực tế vừa gặp, chưa xử lý dứt điểm trong commit hiện tại |
| SSE broker là in-memory                            | 🟡 Trung bình | Hợp single-instance, chưa phù hợp multi-instance                  |
| SQLite phù hợp local/internal nhỏ                  | 🟡 Trung bình | Nếu scale lớn nên cân nhắc PostgreSQL                             |
| Frontend dashboard orchestration còn dày           | 🟡 Trung bình | Nên tách dần logic khỏi `page.tsx`                                |
| Phụ thuộc upstream ChatGPT internal/team APIs      | 🔴 Cao        | Nếu upstream đổi contract, backend có thể hỏng                    |
| Browser/token refresher phụ thuộc automation ngoài | 🟡 Trung bình | Cần theo dõi khi UI/upstream thay đổi                             |

---

## 🏥 Đánh giá sức khỏe hiện tại

### Tốt ở đâu?

- codebase có cấu trúc rõ ràng
- README khá đầy đủ
- luồng nghiệp vụ chính đã có hình hài hoàn chỉnh
- có test và tài liệu hỗ trợ tiếp nhận
- phù hợp cho internal operations dashboard

### Cần chú ý ở đâu?

- bug invite persistence vẫn là issue mở
- các flow sync/invite/unauthorized là nhóm nhạy cảm nhất
- nếu chuẩn bị production hóa mạnh, cần review thêm security, scaling, observability

---

## 📌 Kết luận cuối

Nếu mô tả project này cho người mới tiếp nhận, em sẽ nói như sau:

> Đây là một dashboard quản lý nhiều workspace ChatGPT Team bằng Next.js + FastAPI.  
> Hệ thống cho phép import workspace, sync dữ liệu, quản lý member/invite, phát hiện unauthorized member, refresh token và cập nhật gần realtime qua SSE.  
> Trạng thái hiện tại của project khá tốt cho mục tiêu nội bộ và single-instance, nhưng vẫn còn một lỗi runtime quan trọng liên quan invite pending bị mất sau refresh mà cần tiếp tục xử lý ở bước sau.

---

## 📝 Đề xuất bước tiếp theo

1. Ưu tiên debug lại **invite persistence lifecycle** với cách tiếp cận hẹp và có log runtime rõ hơn.
2. Khi bug invite ổn, chạy lại full regression suite backend/frontend.
3. Tách bớt orchestration khỏi `frontend/src/app/page.tsx` nếu tiếp tục mở rộng dashboard.
4. Nếu chuẩn bị deploy nghiêm túc hơn, lập plan riêng cho:
   - PostgreSQL
   - shared event bus
   - secret management
   - observability/logging

---

## NEXT STEPS

1️⃣ Muốn em đào sâu riêng phần invite/sync hiện tại  
2️⃣ Muốn em tách ra thành kế hoạch nâng cấp với `/plan`  
3️⃣ Muốn em lưu review này vào knowledge bằng `/save-brain`  
4️⃣ Muốn em tiếp tục đánh giá chất lượng code cụ thể hơn bằng `/audit`
