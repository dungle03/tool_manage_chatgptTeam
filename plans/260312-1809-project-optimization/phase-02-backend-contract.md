# Phase 02: Backend Contract & Use-case Cleanup
Status: ⬜ Pending
Dependencies: Phase 01

## Objective
Chuẩn hóa contract trả về của backend và làm rõ trách nhiệm giữa router với service/use-case để frontend nhận dữ liệu đúng ngay sau action.

## Requirements
### Functional
- [ ] Mọi mutation quan trọng trả về shape nhất quán
- [ ] Action trả được `updated_record` hoặc `updated_summary` khi phù hợp
- [ ] Router giảm logic nghiệp vụ trực tiếp
- [ ] Các fallback với upstream được gom về service layer rõ ràng

### Non-Functional
- [ ] Reliability: Không dùng dữ liệu placeholder cho action tiếp theo
- [ ] Maintainability: Rule nghiệp vụ nằm ở nơi dễ kiểm soát
- [ ] Observability: Có log đủ ngữ cảnh cho action thất bại

## Implementation Steps
1. [ ] Thiết kế action response contract dùng chung
2. [ ] Chuẩn hóa invite actions: create / resend / revoke
3. [ ] Chuẩn hóa member actions: kick / delete / status updates
4. [ ] Chuẩn hóa workspace actions: import / delete / sync trigger
5. [ ] Tách các rule fallback upstream vào service chuyên trách
6. [ ] Thêm structured logs cho từng action quan trọng
7. [ ] Cập nhật tests backend theo contract mới

## Files to Create/Modify
- `backend/app/routers/invites.py` - Giảm logic phân tán, thống nhất response
- `backend/app/routers/workspaces.py` - Chuẩn hóa workspace actions
- `backend/app/services/chatgpt.py` - Fallback, retry, mapping dữ liệu upstream
- `backend/app/services/workspace_sync.py` - Kết nối response với rule sync
- `backend/tests/test_invite_flow.py` - Regression tests
- `backend/tests/test_invite_actions.py` - Contract tests

## Test Criteria
- [ ] Invite create/revoke flow pass ổn định
- [ ] Action response có structure nhất quán
- [ ] Backend test suite liên quan không fail
- [ ] Frontend không cần dựa vào refresh toàn phần để hiểu action result

## Notes
Đây là phase giúp “nói chuyện rõ ràng” giữa backend và frontend. Nếu phase này làm tốt, frontend sẽ nhẹ gánh hơn đáng kể.

---
Next Phase: `phase-03-sync-rules.md`
