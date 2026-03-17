# Phase 07: Testing & QA Hardening
Status: ⬜ Pending
Dependencies: Phase 03, Phase 04, Phase 05, Phase 06

## Objective
Khóa chất lượng feature trước khi merge/rollout: nhanh, mượt, ổn định, ít bug.

## Requirements
### Functional
- [ ] Có backend tests cho rename.
- [ ] Có frontend tests cho toggle + rename dialog.
- [ ] Có checklist manual QA cho 2 modes.
- [ ] Có smoke test cho các action cũ sau khi thêm mode mới.

### Non-Functional
- [ ] Performance: đổi mode nhanh, không lag thấy rõ.
- [ ] Stability: không crash khi realtime event đến liên tục.
- [ ] Regression safety: action cũ vẫn chạy.

## Implementation Steps
1. [ ] Viết backend tests:
   - rename success
   - rename invalid input
   - rename upstream rejection
   - rename workspace deleted/not found
2. [ ] Viết frontend tests:
   - toggle mode
   - persist mode qua reload/mock storage
   - open/close rename dialog
   - rename success updates title
   - rename failure keeps old title
3. [ ] Viết regression tests cho compact view actions: sync/delete/manage.
4. [ ] Tạo manual QA checklist:
   - nhiều team
   - rename trong current view
   - rename trong compact view
   - sync song song khi rename
   - delete khi rename modal mở
5. [ ] Chạy test suite theo cụm và ghi lại kết quả.
6. [ ] Chạy performance sanity pass trên dashboard list dài.

## Files to Create/Modify
- `backend/tests/*` - test rename flow.
- `frontend/src/**/*.test.*` - test toggle/rename UI.
- `docs/*` hoặc plan notes - manual QA checklist nếu cần tách riêng.

## Test Criteria
- [ ] Tất cả test mới pass.
- [ ] Existing tests quan trọng của dashboard không bị gãy.
- [ ] Không có bug rõ ràng khi dùng thực tế với nhiều team.
- [ ] Error copy đủ rõ để user biết phải làm gì khi rename fail.

## Notes
Muốn “không bug” trong thực tế thì phase này là bắt buộc, không được xem là bước phụ.

---
Next Phase: Complete
