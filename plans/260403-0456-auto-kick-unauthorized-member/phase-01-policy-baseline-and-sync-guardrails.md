# Phase 01: Policy Baseline & Sync Guardrails

Status: ⬜ Pending
Dependencies: None

## Objective

Chốt baseline logic cho feature auto-kick và bảo vệ sync pipeline để detection luôn xảy ra trước khi local DB bị ghi đè.

## Requirements

### Functional

- [ ] Xác nhận local DB trước sync là whitelist chính thức.
- [ ] Xác nhận policy chỉ áp dụng cho member, không xử lý pending invite.
- [ ] Xác nhận flow add member hợp lệ qua tool được ghi nhận đúng để không false positive.
- [ ] Xác nhận workspace policy mode có thể bật/tắt độc lập.

### Non-Functional

- [ ] Logic phải dễ giải thích cho user vận hành.
- [ ] Không làm đổi behavior sync hiện có ngoài những điểm cần thiết.
- [ ] Có guardrails rõ ràng để debug nếu detection sai.

## Implementation Steps

1. [ ] Map sync flow hiện tại: router/service/background path nào chịu trách nhiệm fetch members.
2. [ ] Xác định điểm đọc local DB trước sync.
3. [ ] Xác định điểm remote fetch hoàn tất nhưng local chưa persist.
4. [ ] Chốt normalized identity key để so sánh member (`email` ưu tiên, `remote_id` nếu có).
5. [ ] Chốt rule ngoại lệ cho member vừa được add hợp lệ qua tool.
6. [ ] Chốt setting/policy level theo workspace.

## Files to Create/Modify

- `backend/app/services/sync.py` - xác định vị trí cấy guardrails detection.
- `backend/app/models.py` - thêm model/policy nếu cần.
- `backend/app/schemas.py` - shape dữ liệu trả về policy state.
- `docs/specs/auto_kick_unauthorized_member_spec.md` - spec tổng hợp.

## Test Criteria

- [ ] Có tài liệu rõ sync-before-write requirement.
- [ ] Có danh sách edge cases chính cần cover ở các phase sau.
- [ ] Có rule normalization email thống nhất.

## Notes

Nếu phase này không khóa chặt thứ tự sync pipeline, các phase sau rất dễ làm ra false positive hoặc mất dấu member lạ.

---

Next Phase: `phase-02-detection-model-and-backend-contracts.md`
