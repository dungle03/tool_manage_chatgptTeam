# Phase 03: Sync Pipeline Detection Logic

Status: ⬜ Pending
Dependencies: Phase 02

## Objective

Cắm detection logic vào sync pipeline sao cho member lạ luôn được phát hiện từ diff giữa local-before-sync và remote-after-fetch.

## Requirements

### Functional

- [ ] Chụp được local member snapshot trước sync.
- [ ] Fetch được remote member list đầy đủ.
- [ ] Tính được diff unauthorized trước khi persist local DB.
- [ ] Detection lặp lại nhiều lần không tạo dữ liệu rác hoặc ghi sai trạng thái.

### Non-Functional

- [ ] Detection phải deterministic.
- [ ] So sánh phải normalize dữ liệu ổn định.
- [ ] Không làm sync chậm quá mức hoặc khó maintain.

## Implementation Steps

1. [ ] Refactor sync flow để có biến `local_members_before_sync` rõ ràng.
2. [ ] Refactor remote fetch result thành `remote_members_after_fetch` rõ ràng.
3. [ ] Viết helper so sánh member sets.
4. [ ] Loại trừ các member hợp lệ do tool vừa tạo nếu cần exception window.
5. [ ] Gắn findings vào sync result trước khi local DB update.
6. [ ] Persist findings hoặc emit events phù hợp.
7. [ ] Chỉ sau đó mới update bảng `members` local.

## Files to Create/Modify

- `backend/app/services/sync.py` - điểm chính cho detection logic.
- `backend/app/services/chatgpt.py` - nếu cần enrich member payload.
- `backend/app/services/events.py` - emit unauthorized detection event.
- `backend/tests/test_sync_service.py` - regression tests detection flow.

## Test Criteria

- [ ] Case local 6 / remote 7 -> detect đúng 1 unauthorized.
- [ ] Case remote trùng local nhưng khác casing email -> không false positive.
- [ ] Case sync lặp lại khi finding chưa xử lý -> behavior idempotent rõ ràng.
- [ ] Case local DB update fail sau detection -> finding không mất dấu.

## Notes

Đây là phase kỹ thuật quan trọng nhất. Nếu flow detect xảy ra sau persist local members, feature coi như mất giá trị.

---

Next Phase: `phase-04-enforcement-modes-and-kick-execution.md`
