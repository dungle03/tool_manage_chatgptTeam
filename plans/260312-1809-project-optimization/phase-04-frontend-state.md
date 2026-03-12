# Phase 04: Frontend State Refactor
Status: ⬜ Pending
Dependencies: Phase 03

## Objective
Tách logic điều phối khỏi `frontend/src/app/page.tsx`, giúp frontend dễ hiểu hơn, ít chồng chéo hơn và sẵn sàng cho tối ưu hiệu năng.

## Requirements
### Functional
- [ ] Tách quản lý workspace list thành hook riêng
- [ ] Tách workspace detail state thành hook riêng
- [ ] Tách action handlers thành hook hoặc module riêng
- [ ] Tách SSE/event handling khỏi UI rendering logic

### Non-Functional
- [ ] Maintainability: `page.tsx` giảm gánh logic đáng kể
- [ ] Performance: Giảm re-render lan rộng
- [ ] Reliability: Refresh policy dễ kiểm soát hơn

## Implementation Steps
1. [ ] Tạo `useWorkspaceList()`
2. [ ] Tạo `useWorkspaceDetails()`
3. [ ] Tạo `useWorkspaceEvents()`
4. [ ] Tạo `useWorkspaceActions()`
5. [ ] Chuyển toast/action status sang mô hình dễ tái sử dụng hơn
6. [ ] Giảm trực tiếp mutation logic trong `page.tsx`
7. [ ] Cập nhật component props theo state mới

## Files to Create/Modify
- `frontend/src/app/page.tsx` - Giảm vai trò orchestration trực tiếp
- `frontend/src/hooks/use-workspace-list.ts` - Hook mới
- `frontend/src/hooks/use-workspace-details.ts` - Hook mới
- `frontend/src/hooks/use-workspace-events.ts` - Hook mới
- `frontend/src/hooks/use-workspace-actions.ts` - Hook mới
- `frontend/src/lib/api.ts` - Kiểu dữ liệu thống nhất hơn

## Test Criteria
- [ ] `page.tsx` ngắn gọn hơn, dễ đọc hơn
- [ ] Event, fetch, action không còn trộn quá chặt vào nhau
- [ ] Các flow cũ vẫn chạy sau refactor

## Notes
Không cần tách quá nhỏ ngay từ đầu. Ưu tiên tách theo “trách nhiệm” trước, rồi mới tối ưu sâu hơn.

---
Next Phase: `phase-05-dashboard-performance.md`
