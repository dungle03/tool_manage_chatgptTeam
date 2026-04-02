# Phase 04: Enforcement Modes & Kick Execution

Status: ⬜ Pending
Dependencies: Phase 03

## Objective

Biến finding unauthorized thành hành động thực tế theo mode vận hành của workspace: tắt, cảnh báo, hoặc tự kick.

## Requirements

### Functional

- [ ] Có 3 mode rõ ràng: `off`, `warn_only`, `auto_kick`.
- [ ] Khi `warn_only`, chỉ tạo finding và hiển thị cảnh báo.
- [ ] Khi `auto_kick`, backend tự gọi remove member.
- [ ] Ghi lại kết quả kick thành công/thất bại với reason rõ ràng.

### Non-Functional

- [ ] Hành vi enforcement phải dễ audit.
- [ ] Không auto-kick khi policy chưa bật rõ ràng.
- [ ] Failure không được làm mất finding gốc.

## Implementation Steps

1. [ ] Thêm config/policy mode theo workspace.
2. [ ] Nối detection result vào decision engine `off / warn_only / auto_kick`.
3. [ ] Viết service kick unauthorized member với reason code thống nhất.
4. [ ] Capture result: `kicked`, `kick_failed`, `already_removed`, `permission_denied`.
5. [ ] Emit event/log để dashboard và debug tools nhìn được lịch sử.
6. [ ] Thêm retry/fallback rule tối thiểu nếu upstream lỗi tạm thời.

## Files to Create/Modify

- `backend/app/services/member_service.py` - encapsulate unauthorized kick logic.
- `backend/app/services/sync.py` - trigger enforcement based on policy.
- `backend/app/routers/workspaces.py` - update policy mode endpoint nếu cần.
- `backend/tests/test_member_enforcement.py` - test auto-kick decisions.

## Test Criteria

- [ ] Mode `off` không kick.
- [ ] Mode `warn_only` không kick nhưng vẫn có finding.
- [ ] Mode `auto_kick` kick đúng member lạ.
- [ ] Upstream kick fail vẫn giữ finding + error state.

## Notes

Phase này chỉ nên làm sau khi detection ổn định. Nếu chưa chắc detection đúng mà bật auto-kick sớm thì rủi ro false positive rất cao.

---

Next Phase: `phase-05-dashboard-visibility-and-controls.md`
