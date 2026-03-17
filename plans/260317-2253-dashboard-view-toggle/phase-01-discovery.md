# Phase 01: Discovery & Guardrails
Status: ⬜ Pending
Dependencies: None

## Objective
Hiểu thật rõ nền hiện tại và khóa các rủi ro lớn nhất trước khi code: vị trí UI toggle, component boundary, upstream rename mechanism, và các tình huống race cần guard.

## Requirements
### Functional
- [ ] Xác định file/component nào đang render workspace list và action icons.
- [ ] Xác định nơi phù hợp để cắm state `dashboardViewMode`.
- [ ] Xác nhận upstream rename workspace path có thể gọi được từ backend.
- [ ] Ghi lại fallback behavior khi rename không khả dụng hoặc bị từ chối.

### Non-Functional
- [ ] Stability: không sửa sâu code trước khi có endpoint/flow rõ.
- [ ] Maintainability: ghi lại dependency map của feature.
- [ ] Performance: không thêm fetch/network loop thừa cho bước verify.

## Implementation Steps
1. [ ] Review `frontend/src/app/page.tsx` và các component workspace hiện tại.
2. [ ] Xác định component mới cần tạo cho compact view, tránh nhồi thêm quá nhiều logic vào `page.tsx`.
3. [ ] Kiểm tra `backend/app/services/chatgpt.py` và router hiện có để tìm pattern call upstream phù hợp.
4. [ ] Xác minh rename workspace bằng network pattern/documentation hoặc existing service behavior.
5. [ ] Ghi lại risk matrix: rename + sync, rename + delete, rename + stale summary.
6. [ ] Chốt nguyên tắc rollout: current view là baseline, compact view là additive feature.

## Files to Create/Modify
- `frontend/src/app/page.tsx` - review point, chưa sửa lớn ở phase này.
- `frontend/src/components/*` - xác định component boundaries.
- `backend/app/services/chatgpt.py` - kiểm tra integration pattern.
- `backend/app/routers/workspaces.py` - kiểm tra route placement cho rename.

## Test Criteria
- [ ] Có tài liệu rõ endpoint/pattern rename trước khi bắt đầu Phase 03.
- [ ] Có danh sách race conditions cần cover trong test.
- [ ] Có chốt vị trí toggle và compact view container.

## Notes
Nếu upstream rename quá mơ hồ, phase này phải dừng lại để `/design` chốt fallback rõ, không được nhảy thẳng sang code UI rename.

---
Next Phase: `phase-02-ux-contract.md`
