# Phase 05: Dashboard UX & Performance Pass
Status: ⬜ Pending
Dependencies: Phase 04

## Objective
Tối ưu cảm giác sử dụng thật: ít giật, ít lag, phản hồi nhanh, trạng thái rõ ràng hơn sau mỗi thao tác.

## Requirements
### Functional
- [ ] Sau action, user thấy trạng thái dễ hiểu hơn
- [ ] Loading/syncing hiển thị theo khu vực liên quan
- [ ] Action bị chống spam click cơ bản
- [ ] Dashboard render ít thừa hơn

### Non-Functional
- [ ] Performance: Giảm cảm giác khựng khi thao tác liên tiếp
- [ ] UX: User biết hệ thống đang xử lý ở giai đoạn nào
- [ ] Accessibility: Nút/action states rõ ràng hơn

## Implementation Steps
1. [ ] Rà re-render hotspots sau khi tách hooks
2. [ ] Memo hóa lại các component cần thiết
3. [ ] Thêm loading states theo vùng
4. [ ] Chuẩn hóa busy/disabled states cho action buttons
5. [ ] Cải thiện toast/message theo lifecycle thực tế
6. [ ] Thêm action queue hoặc anti-double-click guard nếu cần
7. [ ] Đánh giá lại sorted rendering và render cost của dashboard

## Files to Create/Modify
- `frontend/src/app/page.tsx` - Tinh gọn render tree
- `frontend/src/components/member-table.tsx` - Memo/render optimization
- `frontend/src/components/invite-list.tsx` - Busy state rõ hơn
- `frontend/src/components/invite-panel.tsx` - Status messaging rõ hơn
- `frontend/src/styles/*` hoặc CSS liên quan - Trạng thái loading/disabled

## Test Criteria
- [ ] Dashboard phản hồi nhanh hơn khi thao tác liên tiếp
- [ ] User phân biệt được “đang xử lý”, “đã xong local”, “đang đồng bộ”
- [ ] Không phát sinh bug mới do chống spam click

## Notes
Phase này chỉ nên làm mạnh sau khi state architecture đã rõ hơn. Nếu làm sớm quá sẽ chỉ là vá triệu chứng.

---
Next Phase: `phase-06-integration-testing.md`
