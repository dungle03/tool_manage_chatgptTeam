# Phase 04: Frontend View Toggle
Status: ⬜ Pending
Dependencies: Phase 02

## Objective
Thêm cơ chế chuyển view mượt, nhanh và không ảnh hưởng flow hiện có.

## Requirements
### Functional
- [ ] Người dùng có thể chuyển giữa 2 mode bằng một control rõ ràng.
- [ ] View mode được giữ lại sau reload.
- [ ] Current view render y như hiện tại.
- [ ] Compact view dùng chung data/action source.

### Non-Functional
- [ ] Performance: đổi view không refetch toàn bộ danh sách mặc định.
- [ ] Stability: không làm vỡ sync, delete, import, member details.
- [ ] Maintainability: logic view mode nên tách rõ khỏi action logic.

## Implementation Steps
1. [ ] Thêm type/state `dashboardViewMode`.
2. [ ] Đọc/ghi preference từ localStorage an toàn ở client.
3. [ ] Tạo toggle control với active visual state.
4. [ ] Refactor vùng render workspace list để hỗ trợ 2 presentation modes.
5. [ ] Giữ nguyên action handlers hiện có (`sync`, `delete`, `manage`, v.v.).
6. [ ] Kiểm tra re-render hotspots và memo hóa nếu cần.

## Files to Create/Modify
- `frontend/src/app/page.tsx` - orchestration view mode.
- `frontend/src/components/dashboard-view-toggle.tsx` - component mới.
- `frontend/src/types/api.ts` - chỉ sửa nếu cần type UI helper riêng.
- `frontend/src/lib/*` - helper persistence nếu cần.

## Test Criteria
- [ ] Toggle render đúng active mode.
- [ ] Reload trang vẫn nhớ mode trước.
- [ ] Chuyển mode không mất state list hiện có.
- [ ] Chuyển mode không tự gây lỗi loading/realtime.

## Notes
Phase này cố tình tách khỏi compact UI chi tiết để dễ debug. Toggle xong mới lắp view mới.

---
Next Phase: `phase-05-compact-view.md`
