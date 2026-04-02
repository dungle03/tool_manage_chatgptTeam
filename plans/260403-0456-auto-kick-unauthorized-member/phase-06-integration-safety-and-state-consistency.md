# Phase 06: Integration Safety & State Consistency

Status: ⬜ Pending
Dependencies: Phase 05

## Objective

Đảm bảo unauthorized detection, kick result, sync refresh và dashboard state luôn khớp nhau, không tạo trạng thái sai hoặc nhấp nháy khó hiểu.

## Requirements

### Functional

- [ ] Sync event không overwrite finding/kick state sai.
- [ ] Manual refresh không làm mất finding chưa xử lý.
- [ ] Sau kick thành công, local DB và UI phản ánh đúng member đã bị loại khỏi team.
- [ ] Restart app vẫn nhìn lại được trạng thái cần thiết nếu chọn persist findings.

### Non-Functional

- [ ] State transitions dễ debug.
- [ ] Giảm re-fetch thừa.
- [ ] Tránh race condition giữa background sync và user actions.

## Implementation Steps

1. [ ] Chốt source-of-truth cho unauthorized finding lifecycle.
2. [ ] Chốt event/update flow sau detect và sau kick.
3. [ ] Xử lý race: sync đang chạy, user bấm kick tay, hoặc auto-kick vừa xong.
4. [ ] Đảm bảo local DB member list không ghi ngược member đã kick.
5. [ ] Đảm bảo workspace summary/badge update đúng lúc.
6. [ ] Review restart/reload behavior cho dashboard.

## Files to Create/Modify

- `backend/app/services/events.py` - event propagation nếu cần.
- `backend/app/services/sync.py` - ordering safety.
- `frontend/src/app/page.tsx` - state reconciliation.
- `frontend/src/hooks/*` - nếu tách riêng policy/finding state.

## Test Criteria

- [ ] Kick xong thì finding chuyển lifecycle đúng.
- [ ] Background sync không resurrect member đã kick.
- [ ] Refresh dashboard không làm count unauthorized sai.
- [ ] Race scenario có behavior xác định rõ.

## Notes

Phase này là phần “chống hỏng vặt”. Nếu bỏ qua, feature có thể đúng về logic nhưng nhìn trên dashboard vẫn gây mất niềm tin.

---

Next Phase: `phase-07-testing-qa-and-rollout.md`
