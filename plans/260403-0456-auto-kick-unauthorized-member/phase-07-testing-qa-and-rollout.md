# Phase 07: Testing, QA & Rollout

Status: ⬜ Pending
Dependencies: Phase 06

## Objective

Khóa chất lượng feature trước khi bật thật trên workspace sản xuất và giảm rủi ro false positive.

## Requirements

### Functional

- [ ] Có regression suite cho detection logic.
- [ ] Có test cho mode `off`, `warn_only`, `auto_kick`.
- [ ] Có manual QA checklist cho dashboard behavior.
- [ ] Có rollout strategy theo từng mức an toàn.

### Non-Functional

- [ ] Dễ lặp lại test sau mỗi lần upstream thay đổi.
- [ ] Có đủ logs để điều tra nếu false positive xảy ra.
- [ ] Có khả năng rollback policy mode nhanh.

## Implementation Steps

1. [ ] Viết test backend cho diff detection.
2. [ ] Viết test backend cho auto-kick success/failure.
3. [ ] Viết test UI cho unauthorized badges/panel/mode toggle.
4. [ ] Tạo manual QA checklist cho case tool tắt -> member lạ vào -> tool bật lại.
5. [ ] Tạo rollout plan: test workspace -> warn_only -> auto_kick.
6. [ ] Tạo checklist rollback nếu phát hiện false positive.

## Files to Create/Modify

- `backend/tests/test_sync_service.py`
- `backend/tests/test_member_enforcement.py`
- `frontend/tests/*`
- `docs/reports/auto_kick_qa_checklist.md` - QA checklist nếu cần

## Test Criteria

- [ ] Scenario chuẩn của user được pass end-to-end.
- [ ] Không có false positive với member đã có trong local DB.
- [ ] Warn-only và auto-kick cho ra logs rõ ràng.
- [ ] Rollback mode về `off` không làm hỏng dữ liệu hiện có.

## Notes

Rollout tốt nhất là thử trên 1 workspace test trước, sau đó mới mở rộng. Với feature dạng governance như này, rollout chậm mà chắc sẽ tốt hơn nhiều so với bật đại trà ngay.

---

Next Phase: Complete
