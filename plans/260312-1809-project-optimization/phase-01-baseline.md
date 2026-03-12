# Phase 01: Baseline & Guardrails
Status: ⬜ Pending
Dependencies: None

## Objective
Thiết lập baseline hiện trạng để các phase sau refactor an toàn, đo được tiến triển, và không phá vỡ flow đang chạy.

## Requirements
### Functional
- [ ] Liệt kê đầy đủ các flow quan trọng hiện tại
- [ ] Chụp baseline response contract của các mutation chính
- [ ] Xác định các điểm đang phụ thuộc vào refresh tổng thể
- [ ] Xác định các edge case đã biết và cần regression test

### Non-Functional
- [ ] Performance: Có baseline định tính cho dashboard responsiveness
- [ ] Reliability: Có danh sách flow không được phép vỡ sau refactor
- [ ] Maintainability: Có bản đồ file/module đang gánh logic lớn

## Implementation Steps
1. [ ] Lập inventory flow nghiệp vụ hiện có
2. [ ] Lập inventory API mutation response hiện tại
3. [ ] Lập inventory các nguồn refresh/invalidate trên frontend
4. [ ] Lập inventory sync triggers và follow-up rules ở backend
5. [ ] Xác định 5-8 regression flows bắt buộc giữ ổn định
6. [ ] Tạo checklist kiểm tra tay cho các flow nhạy cảm
7. [ ] Ghi lại hotspot files cần refactor ưu tiên

## Files to Create/Modify
- `docs/specs/project_optimization_spec.md` - Spec tổng thể
- `plans/260312-1809-project-optimization/plan.md` - Tracker chung
- `frontend/src/app/page.tsx` - Chỉ đọc/đánh dấu hotspot, chưa refactor sâu
- `backend/app/services/workspace_sync.py` - Chỉ phân tích rule, chưa refactor sâu

## Test Criteria
- [ ] Có danh sách regression flow được viết ra rõ ràng
- [ ] Có thể giải thích vì sao từng flow quan trọng
- [ ] Có baseline đủ để so sánh sau khi tối ưu

## Notes
Phase này không cố sửa toàn bộ vấn đề. Mục tiêu là chuẩn bị “lan can an toàn” trước khi đụng vào các phần nhạy cảm.

---
Next Phase: `phase-02-backend-contract.md`
