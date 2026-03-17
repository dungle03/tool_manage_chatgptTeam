# Phase 03: Backend Rename API
Status: ⬜ Pending
Dependencies: Phase 01, Phase 02

## Objective
Thêm luồng backend đổi tên workspace thật, an toàn và dễ debug.

## Requirements
### Functional
- [ ] Có endpoint backend rename workspace.
- [ ] Backend xác thực workspace tồn tại và có dữ liệu cần thiết để rename.
- [ ] Backend gọi upstream/internal API để đổi tên thật.
- [ ] Backend cập nhật DB local summary sau rename thành công.
- [ ] Backend trả response contract nhất quán cho frontend.

### Non-Functional
- [ ] Reliability: rename fail không làm hỏng workspace record local.
- [ ] Observability: log được org_id, rename target, result, fallback path.
- [ ] Security: sanitize input name, chặn rename rỗng hoặc quá dài.

## Implementation Steps
1. [ ] Thêm request schema cho rename workspace.
2. [ ] Thêm route trong workspace router, ví dụ `PATCH /api/workspaces/{org_id}/name`.
3. [ ] Thêm service method trong `chatgpt.py` hoặc dedicated workspace service để gọi upstream rename.
4. [ ] Validate quyền/tokens trước khi gọi upstream.
5. [ ] Nếu upstream trả thành công, cập nhật `Workspace.name` ở DB local.
6. [ ] Trả về `updated_summary` + `refresh_hint`.
7. [ ] Chuẩn hóa error mapping: unauthorized, forbidden, upstream rejection, workspace missing.
8. [ ] Bổ sung structured log cho rename flow.

## Files to Create/Modify
- `backend/app/routers/workspaces.py` - route rename.
- `backend/app/services/chatgpt.py` - upstream rename call.
- `backend/app/services/workspace_sync.py` - chỉ chỉnh nếu cần tránh overwrite tên sai sau sync.
- `backend/app/models.py` - review nếu cần field hỗ trợ, thường không cần schema mới.
- `backend/tests/*` - thêm test backend.

## Test Criteria
- [ ] Rename thành công cập nhật DB local và response có `updated_summary`.
- [ ] Rename fail không đổi tên local.
- [ ] Workspace không tồn tại trả lỗi rõ.
- [ ] Input invalid bị chặn trước khi gọi upstream.

## Notes
Nếu upstream rename dùng internal endpoint không ổn định, cần bọc logic thành service riêng để sau này dễ sửa hơn.

---
Next Phase: `phase-04-frontend-toggle.md`
