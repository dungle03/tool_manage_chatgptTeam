# Sync & Realtime Runbook

## Mục tiêu
Tài liệu này dùng cho người vận hành hoặc người maintain dự án khi cần:
- hiểu sync engine đang quyết định gì
- debug dashboard không tự cập nhật
- debug workspace bị kẹt ở trạng thái `syncing` hoặc `error`
- chạy lại test đúng cách sau khi sửa backend/frontend

---

## 1. Nguồn sự thật hiện tại

### Backend là nguồn sự thật cuối cùng
- Dữ liệu member/invite/workspace được chốt ở backend
- Frontend chỉ áp dụng cập nhật cục bộ để phản hồi nhanh hơn
- Sau mutation, frontend vẫn dựa vào `updated_summary`, `updated_record`, `refresh_hint` và/hoặc refresh hẹp để đồng bộ lại

### Frontend local state chỉ là lớp hiển thị tạm
- Có thể thêm/xóa/cập nhật record trước để UI mượt hơn
- Không nên xem local state là trạng thái chuẩn cuối cùng
- Khi nghi ngờ lệch dữ liệu, ưu tiên refresh đúng scope thay vì cố vá bằng logic UI

---

## 2. Sync engine đang chạy theo rule nào

File chính: `backend/app/services/workspace_sync.py`

### Các nhóm lịch sync hiện tại
1. **Baseline refresh**
   - áp dụng khi workspace không còn ở hot window
   - reason: `baseline_refresh`

2. **Follow-up sync**
   - áp dụng sau action quan trọng hoặc khi workspace còn trong hot window
   - reason dạng `followup:<index>`
   - step mặc định lấy từ `SYNC_FOLLOWUP_STEPS=5,15,30,60`

3. **Pending invite watch**
   - áp dụng khi còn invite `pending`
   - reason: `pending_invite_watch`
   - delay mặc định lấy từ `SYNC_PENDING_INVITE_SECONDS`

4. **Retry after error**
   - áp dụng khi sync thất bại
   - reason: `retry_after_error`
   - delay mặc định lấy step đầu của `SYNC_ERROR_RETRY_STEPS`

### Priority hiện tại
- `pending invites` => ưu tiên cao nhất
- `hot window` => ưu tiên cao
- `status=error` => ưu tiên retry
- còn lại => baseline/cold refresh

---

## 3. Khi nào frontend nên refresh gì

### Chỉ refresh workspace list
Dùng khi mutation chỉ ảnh hưởng summary mức workspace:
- delete workspace
- thay đổi sync status
- thay đổi `pending_invites`, `member_count`, `last_sync`

### Refresh workspace detail
Dùng khi đang mở detail và cần đồng bộ lại members/invites:
- kick member
- resend / revoke invite
- create invite
- sync xong và detail đã từng được load

### Ưu tiên `refresh_hint`
Nếu backend trả `refresh_hint`, frontend nên đi theo scope đó thay vì tự đoán toàn bộ.

---

## 4. Checklist debug nhanh

### Case A — bấm action xong nhưng UI không đổi
1. Kiểm tra response mutation có trả:
   - `updated_summary`
   - `updated_record` nếu cần
   - `refresh_hint`
2. Kiểm tra `page.tsx` hoặc helper đang apply đúng payload chưa
3. Kiểm tra workspace detail đã `loadedMembers=true` chưa
4. Nếu nghi SSE không tới, thử manual refresh hẹp

### Case B — workspace bị `syncing` quá lâu
1. Kiểm tra backend log khi gọi `/api/workspaces/{orgId}/sync`
2. Kiểm tra event `sync_started` có tới frontend không
3. Kiểm tra có `workspace_updated` hoặc `sync_failed` sau đó không
4. Nếu không có event kết thúc, xem worker/background loop hoặc upstream API call có bị lỗi

### Case C — workspace chuyển sang `error`
1. Xem `sync_error` trên workspace
2. Xác nhận token/session token còn hợp lệ
3. Kiểm tra upstream response khi gọi member/invite endpoints
4. Kiểm tra `retry_after_error` đã được schedule chưa

### Case D — vừa action xong nhưng dữ liệu lại bị “bật ngược”
1. Xem local optimistic update có conflict với refresh hẹp hay SSE không
2. Xem backend có đang trả summary/record cũ không
3. Ưu tiên fix ở backend contract trước khi thêm vá ở frontend

---

## 5. Cách verify sau khi sửa code

### Frontend
Chạy trong `frontend/`:

```powershell
npm test
```

Nếu vừa sửa riêng luồng realtime/SSE helper, có thể chạy hẹp hơn:

```powershell
npm test -- workspace-events.test.ts
```

> Lưu ý trên Windows: ưu tiên đi qua script `npm test` của repo để dùng launcher Vitest theo real path. Không nên gọi `npx vitest` trực tiếp nếu chưa chắc config path đang đúng.

### Backend
Khuyến nghị chạy từ repo root:

```powershell
./run_backend_tests.ps1
```

Hoặc chạy trực tiếp trong `backend/`:

```powershell
pytest -q
```

Nếu vừa sửa riêng nhánh sync/realtime:

```powershell
pytest backend/tests/test_realtime_sync.py -q
```


---

## 6. Các file nên xem đầu tiên khi có lỗi

### Backend
- `backend/app/services/workspace_sync.py`
- `backend/app/services/events.py`
- `backend/app/routers/workspaces.py`
- `backend/app/routers/invites.py`
- `backend/tests/test_realtime_sync.py`
- `backend/tests/test_invite_flow.py`
- `backend/tests/test_invite_actions.py`
- `backend/tests/test_phase12_endpoint_contract.py`

### Frontend
- `frontend/src/app/page.tsx`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/workspace-state.ts`
- `frontend/src/components/invite-panel.tsx`
- `frontend/src/components/import-dialog.tsx`
- `frontend/src/__tests__/workspace-state.test.ts`
- `frontend/src/__tests__/workspace-events.test.ts`

### Realtime/SSE checklist nhanh
- Xác nhận `buildWorkspaceEventsUrl()` đang gắn `admin_token` đúng khi có `NEXT_PUBLIC_ADMIN_TOKEN`
- Xác nhận event malformed không làm UI crash
- Xác nhận `heartbeat` / `workspace_updated` / `sync_failed` vẫn parse được ở frontend
- Nếu debug auth SSE, xem `backend/app/routers/events.py` cùng `verify_sse_admin_token()` trước khi nghi frontend

---

## 7. Nguyên tắc maintain tiếp theo

- Nếu logic là rule dùng lại nhiều lần, tách helper thay vì nhét tiếp vào `page.tsx`
- Nếu logic là rule nguồn sự thật, ưu tiên nằm ở backend
- Nếu mutation contract đổi, phải cập nhật test backend trước hoặc cùng lúc
- Nếu frontend phải đoán quá nhiều sau mutation, đó là tín hiệu backend contract còn thiếu

---

## 8. Dấu hiệu đã ổn

Có thể xem flow là ổn khi:
- mutation trả contract nhất quán
- UI cập nhật đúng mà không cần F5 toàn trang
- sync worker schedule được follow-up/retry hợp lý
- frontend/backend tests đều pass sau refactor
- realtime helper và SSE/auth path vẫn có regression coverage tối thiểu sau mỗi lần chỉnh luồng realtime
