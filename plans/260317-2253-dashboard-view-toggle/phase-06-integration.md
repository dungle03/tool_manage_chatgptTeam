# Phase 06: Integration & State Safety
Status: ⬜ Pending
Dependencies: Phase 03, Phase 04, Phase 05

## Objective
Nối rename thật và compact view vào dashboard hiện có mà không tạo bug state chồng chéo.

## Requirements
### Functional
- [ ] Rename modal mở từ cả compact view và current view nếu muốn đồng nhất.
- [ ] Rename thành công cập nhật đúng summary hiện tại.
- [ ] Rename thất bại giữ nguyên UI cũ.
- [ ] Realtime/sync vẫn tiếp tục hoạt động đúng sau rename.

### Non-Functional
- [ ] Consistency: không để SSE hoặc refresh chậm ghi đè tên mới sai cách.
- [ ] Resilience: xử lý được race rename + sync/delete.
- [ ] UX: loading/disabled state rõ khi đang rename.

## Implementation Steps
1. [ ] Thêm API client frontend cho rename workspace.
2. [ ] Tạo modal/dialog rename với validation cơ bản.
3. [ ] Submit rename → chờ backend response → apply `updated_summary` targeted.
4. [ ] Nếu cần, trigger refresh nhẹ theo `refresh_hint`.
5. [ ] Guard trường hợp workspace bị delete trong khi modal đang mở.
6. [ ] Guard trường hợp sync event về ngay sau rename.
7. [ ] Đảm bảo expanded/detail state không bị reset vô ích khi rename thành công.

## Files to Create/Modify
- `frontend/src/lib/api.ts` - thêm rename API call.
- `frontend/src/app/page.tsx` - nối rename handler.
- `frontend/src/components/rename-workspace-dialog.tsx` - component mới.
- `frontend/src/lib/workspace-state.ts` - helper targeted summary update nếu cần mở rộng.
- `backend/app/routers/workspaces.py` - integration contract đối chiếu.

## Test Criteria
- [ ] Rename success cập nhật title ngay không cần full reload.
- [ ] Rename failure không làm hỏng local state.
- [ ] Rename trong compact view và current view đều consistent.
- [ ] Workspace bị delete/sync trong lúc rename không làm UI crash.

## Notes
Đây là phase dễ sinh bug nhất vì chạm cả UI state, backend response, và event refresh. Phải làm chậm mà chắc.

---
Next Phase: `phase-07-testing.md`
