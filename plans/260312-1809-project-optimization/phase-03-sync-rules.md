# Phase 03: Sync Engine & Source-of-Truth Rules
Status: ⬜ Pending
Dependencies: Phase 02

## Objective
Làm rõ rule đồng bộ dữ liệu để hệ thống vừa đúng vừa không refresh thừa, đồng thời xác định nguồn sự thật cho từng nhóm dữ liệu.

## Requirements
### Functional
- [ ] Có source-of-truth matrix cho workspace/member/invite
- [ ] Có quy tắc rõ cho manual sync, scheduled sync, follow-up sync
- [ ] SSE/event chỉ invalidate đúng phạm vi cần thiết
- [ ] UI biết khi nào dữ liệu là local-confirmed, khi nào upstream-confirmed

### Non-Functional
- [ ] Correctness: Giảm tối đa trạng thái mơ hồ sau action
- [ ] Performance: Tránh sync dày đặc không cần thiết
- [ ] Maintainability: Rule sync đọc vào là hiểu được

## Implementation Steps
1. [ ] Viết source-of-truth matrix cho các field chính
2. [ ] Rà và gom nhóm các trigger sync hiện tại
3. [ ] Chuẩn hóa rule follow-up sync sau từng loại action
4. [ ] Chuẩn hóa refresh hint từ backend sang frontend
5. [ ] Định nghĩa rule invalidate list/detail trên dashboard
6. [ ] Rà lại hot priority / next_sync_at / pending invite priority
7. [ ] Bổ sung test cho sync-in-progress và follow-up scenarios

## Files to Create/Modify
- `backend/app/services/workspace_sync.py` - Rule sync và source-of-truth mapping
- `backend/app/routers/workspaces.py` - Sync trigger behavior
- `frontend/src/app/page.tsx` - Giai đoạn đầu chỉ cập nhật rule invalidate
- `docs/specs/project_optimization_spec.md` - Matrix và decision rules

## Test Criteria
- [ ] Sync đang chạy không gây hành vi khó đoán
- [ ] Action xong biết rõ nên update local, invalidate detail hay refresh summary
- [ ] Không còn nhiều case “đúng nhưng sai thời điểm”

## Notes
Phase này là trung tâm của bài toán. Làm xong phase này thì performance và UI sẽ dễ tối ưu đúng cách hơn.

---
Next Phase: `phase-04-frontend-state.md`
