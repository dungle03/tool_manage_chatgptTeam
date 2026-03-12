# Phase 06: Integration & Regression Hardening
Status: ⬜ Pending
Dependencies: Phase 05

## Objective
Khóa chặt các flow quan trọng bằng test và checklist tích hợp để tránh bug quay lại sau khi tối ưu.

## Requirements
### Functional
- [ ] Có regression test cho các flow nhạy cảm nhất
- [ ] Có checklist kiểm thử tay cho UI behavior thực tế
- [ ] Backend/frontend contract được kiểm tra đồng bộ

### Non-Functional
- [ ] Reliability: Bug cũ khó quay lại hơn
- [ ] Confidence: Có thể refactor tiếp mà ít sợ vỡ hệ thống
- [ ] Traceability: Biết bug nào đã được bảo vệ bởi test nào

## Implementation Steps
1. [ ] Chọn bộ regression flows chính thức
2. [ ] Viết/hoàn thiện backend tests cho flow-level behavior
3. [ ] Viết/hoàn thiện frontend tests cho state/render behavior
4. [ ] Thêm contract checks cho các action response
5. [ ] Tạo manual QA checklist cho các case khó tái hiện bằng unit test
6. [ ] Chạy full verification sau từng nhóm refactor

## Files to Create/Modify
- `backend/tests/*.py` - Regression và contract tests
- `frontend/src/__tests__/*.test.tsx` - UI/state behavior tests
- `docs/specs/project_optimization_spec.md` - Mapping flow -> test coverage
- `plans/260312-1809-project-optimization/reports/` - Báo cáo kiểm thử

## Test Criteria
- [ ] Invite, member, sync, import flows có coverage rõ ràng
- [ ] Test suite pass sau refactor
- [ ] Manual QA checklist chạy được và có kết quả rõ ràng

## Notes
Phase này biến các bài học từ bug thực tế thành tài sản lâu dài của dự án.

---
Next Phase: `phase-07-ops-docs.md`
